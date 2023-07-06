from dataclasses import dataclass
from typing import Callable, List, Optional, Union

import PIL
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from diffusers import StableDiffusionPipeline
from diffusers.models import AutoencoderKL, UNet2DConditionModel
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from diffusers.schedulers import KarrasDiffusionSchedulers
from diffusers.utils import BaseOutput
from einops import rearrange, repeat
from kornia.morphology import dilation
from torch.nn.functional import grid_sample
from transformers import CLIPFeatureExtractor, CLIPTextModel, CLIPTokenizer


@dataclass
class TextToVideoPipelineOutput(BaseOutput):
    images: Union[List[PIL.Image.Image], np.ndarray]
    nsfw_content_detected: Optional[List[bool]]


def coords_grid(batch, ht, wd, device):
    coords = torch.meshgrid(torch.arange(
        ht, device=device), torch.arange(wd, device=device))
    coords = torch.stack(coords[::-1], dim=0).float()
    return coords[None].repeat(batch, 1, 1, 1)


class CrossFrameAttnProcessor:
    def __init__(self, unet_chunk_size=2):
        self.unet_chunk_size = unet_chunk_size

    def __call__(
            self,
            attn,
            hidden_states,
            encoder_hidden_states=None,
            attention_mask=None):
        batch_size, sequence_length, _ = hidden_states.shape
        attention_mask = attn.prepare_attention_mask(attention_mask, sequence_length, batch_size)
        query = attn.to_q(hidden_states)

        is_cross_attention = encoder_hidden_states is not None
        if encoder_hidden_states is None:
            encoder_hidden_states = hidden_states
        elif attn.cross_attention_norm:
            encoder_hidden_states = attn.norm_cross(encoder_hidden_states)
        key = attn.to_k(encoder_hidden_states)
        value = attn.to_v(encoder_hidden_states)
        # Sparse Attention
        if not is_cross_attention:
            video_length = key.size()[0] // self.unet_chunk_size
            # former_frame_index = torch.arange(video_length) - 1
            # former_frame_index[0] = 0
            former_frame_index = [0] * video_length
            key = rearrange(key, "(b f) d c -> b f d c", f=video_length)
            key = key[:, former_frame_index]
            key = rearrange(key, "b f d c -> (b f) d c")
            value = rearrange(value, "(b f) d c -> b f d c", f=video_length)
            value = value[:, former_frame_index]
            value = rearrange(value, "b f d c -> (b f) d c")

        query = attn.head_to_batch_dim(query)
        key = attn.head_to_batch_dim(key)
        value = attn.head_to_batch_dim(value)

        attention_probs = attn.get_attention_scores(query, key, attention_mask)
        hidden_states = torch.bmm(attention_probs, value)
        hidden_states = attn.batch_to_head_dim(hidden_states)

        # linear proj
        hidden_states = attn.to_out[0](hidden_states)
        # dropout
        hidden_states = attn.to_out[1](hidden_states)

        return hidden_states


class StableDiffusionTxt2VideoPipeline(StableDiffusionPipeline):
    _optional_components = ["safety_checker", "feature_extractor"]

    def __init__(
            self,
            vae: AutoencoderKL,
            text_encoder: CLIPTextModel,
            tokenizer: CLIPTokenizer,
            unet: UNet2DConditionModel,
            scheduler: KarrasDiffusionSchedulers,
            safety_checker: StableDiffusionSafetyChecker,
            feature_extractor: CLIPFeatureExtractor,
            requires_safety_checker: bool = False,
    ):
        super().__init__(vae, text_encoder, tokenizer, unet, scheduler,
                         safety_checker, feature_extractor, requires_safety_checker)
        self.unet.set_attn_processor(processor=CrossFrameAttnProcessor(unet_chunk_size=2))
        self.enable_model_cpu_offload()
        self.enable_vae_slicing()

    def DDPM_forward(self, x0, t0, tMax, generator, device, shape, text_embeddings):
        rand_device = "cpu" if device.type == "mps" else device

        if x0 is None:
            return torch.randn(shape, generator=generator, device=rand_device, dtype=text_embeddings.dtype).to(device)
        else:
            eps = torch.randn(x0.shape, dtype=text_embeddings.dtype, generator=generator,
                              device=rand_device)
            alpha_vec = torch.prod(self.scheduler.alphas[t0:tMax])

            xt = torch.sqrt(alpha_vec) * x0 + \
                 torch.sqrt(1 - alpha_vec) * eps
            return xt

    def prepare_latents(self, batch_size, num_channels_latents, video_length, height, width, dtype, device, generator,
                        latents=None):
        shape = (batch_size, num_channels_latents, video_length, height //
                 self.vae_scale_factor, width // self.vae_scale_factor)
        if isinstance(generator, list) and len(generator) != batch_size:
            raise ValueError(
                f"You have passed a list of generators of length {len(generator)}, but requested an effective batch"
                f" size of {batch_size}. Make sure the batch size matches the length of the generators."
            )

        if latents is None:
            rand_device = "cpu" if device.type == "mps" else device

            if isinstance(generator, list):
                shape = (1,) + shape[1:]
                latents = [
                    torch.randn(
                        shape, generator=generator[i], device=rand_device, dtype=dtype)
                    for i in range(batch_size)
                ]
                latents = torch.cat(latents, dim=0).to(device)
            else:
                latents = torch.randn(
                    shape, generator=generator, device=rand_device, dtype=dtype).to(device)
        else:
            latents = latents.to(device)

        # scale the initial noise by the standard deviation required by the scheduler
        latents = latents * self.scheduler.init_noise_sigma
        return latents

    def warp_latents_independently(self, latents, reference_flow):
        _, _, H, W = reference_flow.size()
        b, _, f, h, w = latents.size()
        assert b == 1
        coords0 = coords_grid(f, H, W, device=latents.device).to(latents.dtype)

        coords_t0 = coords0 + reference_flow
        coords_t0[:, 0] /= W
        coords_t0[:, 1] /= H

        coords_t0 = coords_t0 * 2.0 - 1.0

        coords_t0 = T.Resize((h, w))(coords_t0)

        coords_t0 = rearrange(coords_t0, 'f c h w -> f h w c')

        latents_0 = rearrange(latents[0], 'c f h w -> f  c  h w')
        warped = grid_sample(latents_0, coords_t0,
                             mode='nearest', padding_mode='reflection')

        warped = rearrange(warped, '(b f) c h w -> b c f h w', f=f)
        return warped

    def DDIM_backward(self, num_inference_steps, timesteps, skip_t, t0, t1, do_classifier_free_guidance, null_embs,
                      text_embeddings, latents_local,
                      latents_dtype, guidance_scale, guidance_stop_step, callback, callback_steps, extra_step_kwargs,
                      num_warmup_steps):
        entered = False

        f = latents_local.shape[2]

        latents_local = rearrange(latents_local, "b c f w h -> (b f) c w h")

        latents = latents_local.detach().clone()
        x_t0_1 = None
        x_t1_1 = None

        with self.progress_bar(total=num_inference_steps) as progress_bar:
            for i, t in enumerate(timesteps):
                if t > skip_t:
                    continue
                else:
                    if not entered:
                        print(
                            f"Continue DDIM with i = {i}, t = {t}, latent = {latents.shape}, device = {latents.device}, type = {latents.dtype}")
                        entered = True

                latents = latents.detach()
                # expand the latents if we are doing classifier free guidance
                latent_model_input = torch.cat(
                    [latents] * 2) if do_classifier_free_guidance else latents
                latent_model_input = self.scheduler.scale_model_input(
                    latent_model_input, t)

                # predict the noise residual
                with torch.no_grad():
                    if null_embs is not None:
                        text_embeddings[0] = null_embs[i][0]
                    te = torch.cat([repeat(text_embeddings[0, :, :], "c k -> f c k", f=f),
                                    repeat(text_embeddings[1, :, :], "c k -> f c k", f=f)])
                    noise_pred = self.unet(
                        latent_model_input, t, encoder_hidden_states=te).sample.to(dtype=latents_dtype)

                # perform guidance
                if do_classifier_free_guidance:
                    noise_pred_uncond, noise_pred_text = noise_pred.chunk(
                        2)
                    noise_pred = noise_pred_uncond + guidance_scale * \
                                 (noise_pred_text - noise_pred_uncond)

                if i >= guidance_stop_step * len(timesteps):
                    alpha = 0
                # compute the previous noisy sample x_t -> x_t-1
                latents = self.scheduler.step(
                    noise_pred, t, latents, **extra_step_kwargs).prev_sample
                # latents = latents - alpha * grads / (torch.norm(grads) + 1e-10)
                # call the callback, if provided

                if i < len(timesteps) - 1 and timesteps[i + 1] == t0:
                    x_t0_1 = latents.detach().clone()
                    print(f"latent t0 found at i = {i}, t = {t}")
                elif i < len(timesteps) - 1 and timesteps[i + 1] == t1:
                    x_t1_1 = latents.detach().clone()
                    print(f"latent t1 found at i={i}, t = {t}")

                if i == len(timesteps) - 1 or ((i + 1) > num_warmup_steps and (i + 1) % self.scheduler.order == 0):
                    progress_bar.update()
                    if callback is not None and i % callback_steps == 0:
                        callback(i, t, latents)

        latents = rearrange(latents, "(b f) c w h -> b c f  w h", f=f)

        res = {"x0": latents.detach().clone()}
        if x_t0_1 is not None:
            x_t0_1 = rearrange(x_t0_1, "(b f) c w h -> b c f  w h", f=f)
            res["x_t0_1"] = x_t0_1.detach().clone()
        if x_t1_1 is not None:
            x_t1_1 = rearrange(x_t1_1, "(b f) c w h -> b c f  w h", f=f)
            res["x_t1_1"] = x_t1_1.detach().clone()
        return res

    def decode_latents(self, latents):
        latents = 1 / self.vae.config.scaling_factor * latents
        image = self.vae.decode(latents, return_dict=False)[0]
        image = (image / 2 + 0.5).clamp(0, 1)
        # we always cast to float32 as this does not cause significant overhead and is compatible with bfloat16
        image = image.cpu().permute(0, 2, 3, 1).float().numpy()
        return image

    def create_motion_field(self, motion_field_strength_x, motion_field_strength_y, frame_ids, video_length, latents):

        reference_flow = torch.zeros(
            (video_length - 1, 2, 512, 512), device=latents.device, dtype=latents.dtype)
        for fr_idx, frame_id in enumerate(frame_ids):
            reference_flow[fr_idx, 0, :,
            :] = motion_field_strength_x * (frame_id)
            reference_flow[fr_idx, 1, :,
            :] = motion_field_strength_y * (frame_id)
        return reference_flow

    def create_motion_field_and_warp_latents(self, motion_field_strength_x, motion_field_strength_y, frame_ids,
                                             video_length, latents):

        motion_field = self.create_motion_field(motion_field_strength_x=motion_field_strength_x,
                                                motion_field_strength_y=motion_field_strength_y, latents=latents,
                                                video_length=video_length, frame_ids=frame_ids)
        for idx, latent in enumerate(latents):
            latents[idx] = self.warp_latents_independently(
                latent[None], motion_field)
        return motion_field, latents

    @torch.no_grad()
    def __call__(
            self,
            prompt: Union[str, List[str]],
            video_length: Optional[int] = 32,
            height: Optional[int] = None,
            width: Optional[int] = None,
            num_inference_steps: int = 50,
            guidance_scale: float = 7.5,
            guidance_stop_step: float = 0.5,
            negative_prompt: Optional[Union[str, List[str]]] = None,
            eta: float = 0.0,
            generator: Optional[Union[torch.Generator, List[torch.Generator]]] = None,
            xT: Optional[torch.FloatTensor] = None,
            null_embs: Optional[torch.FloatTensor] = None,
            motion_field_strength_x: float = 12,
            motion_field_strength_y: float = 12,
            output_type: Optional[str] = "tensor",
            return_dict: bool = True,
            callback: Optional[Callable[[
                int, int, torch.FloatTensor], None]] = None,
            callback_steps: Optional[int] = 1,
            use_motion_field: bool = True,
            smooth_bg: bool = False,
            smooth_bg_strength: float = 0.4,
            t0: int = 44,
            t1: int = 47,
            **kwargs,
    ):
        r"""
                Function invoked when calling the pipeline for generation.

                Args:
                    prompt (`str` or `List[str]`, *optional*):
                        The prompt or prompts to guide the image generation. If not defined, one has to pass `prompt_embeds`.
                        instead.
                    video_length (`int`, *optional*, defaults to 32):
                    height (`int`, *optional*, defaults to self.unet.config.sample_size * self.vae_scale_factor):
                        The height in pixels of the generated image.
                    width (`int`, *optional*, defaults to self.unet.config.sample_size * self.vae_scale_factor):
                        The width in pixels of the generated image.
                    num_inference_steps (`int`, *optional*, defaults to 50):
                        The number of denoising steps. More denoising steps usually lead to a higher quality image at the
                        expense of slower inference.
                    guidance_scale (`float`, *optional*, defaults to 7.5):
                        Guidance scale as defined in [Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598).
                        `guidance_scale` is defined as `w` of equation 2. of [Imagen
                        Paper](https://arxiv.org/pdf/2205.11487.pdf). Guidance scale is enabled by setting `guidance_scale >
                        1`. Higher guidance scale encourages to generate images that are closely linked to the text `prompt`,
                        usually at the expense of lower image quality.
                    negative_prompt (`str` or `List[str]`, *optional*):
                        The prompt or prompts not to guide the image generation. If not defined, one has to pass
                        `negative_prompt_embeds` instead. Ignored when not using guidance (i.e., ignored if `guidance_scale` is
                        less than `1`).
                    eta (`float`, *optional*, defaults to 0.0):
                        Corresponds to parameter eta (η) in the DDIM paper: https://arxiv.org/abs/2010.02502. Only applies to
                        [`schedulers.DDIMScheduler`], will be ignored for others.
                    generator (`torch.Generator` or `List[torch.Generator]`, *optional*):
                        One or a list of [torch generator(s)](https://pytorch.org/docs/stable/generated/torch.Generator.html)
                        to make generation deterministic.
                    xT (`torch.FloatTensor`, *optional*):
                        Pre-generated text embeddings. Can be used to easily tweak text inputs, *e.g.* prompt weighting. If not
                        provided, text embeddings will be generated from `prompt` input argument.
                    null_embs (`torch.FloatTensor`, *optional*):
                        Pre-generated negative text embeddings. Can be used to easily tweak text inputs, *e.g.* prompt
                    motion_field_strength_y (`float`, *optional*, defaults to 12):
                        The strength of the motion field in the y direction.
                    motion_field_strength_x (`float`, *optional*, defaults to 12):
                        The strength of the motion field in the x direction.
                    output_type (`str`, *optional*, defaults to `"pil"`):
                        The output format of the generate image. Choose between
                        [PIL](https://pillow.readthedocs.io/en/stable/): `PIL.Image.Image` or `np.array`.
                    return_dict (`bool`, *optional*, defaults to `True`):
                        Whether or not to return a [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] instead of a
                        plain tuple.
                    callback (`Callable`, *optional*):
                        A function that will be called every `callback_steps` steps during inference. The function will be
                        called with the following arguments: `callback(step: int, timestep: int, latents: torch.FloatTensor)`.
                    callback_steps (`int`, *optional*, defaults to 1):
                        The frequency at which the `callback` function will be called. If not specified, the callback will be
                        called at every step.
                    use_motion_field (`bool`, *optional*, defaults to `True`):
                        Whether to use the motion field.
                    smooth_bg (`bool`, *optional*, defaults to `False`):
                        Whether to smooth the background.
                    smooth_bg_strength (`float`, *optional*, defaults to 0.4):
                        The strength of the background smoothing.
                    t0 (`int`, *optional*, defaults to 44):
                        The start timestep of the diffusion process.
                    t1 (`int`, *optional*, defaults to 47):
                        The end timestep of the diffusion process.

                Examples:

                Returns:
                    [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] or `tuple`:
                    [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] if `return_dict` is True, otherwise a `tuple.
                    When returning a tuple, the first element is a list with the generated images, and the second element is a
                    list of `bool`s denoting whether the corresponding generated image likely represents "not-safe-for-work"
                    (nsfw) content, according to the `safety_checker`.
                """
        frame_ids = kwargs.pop("frame_ids", list(range(video_length)))
        assert t0 < t1
        assert isinstance(prompt, list) and len(prompt) > 0
        assert isinstance(negative_prompt, list) or negative_prompt is None
        num_videos_per_prompt = 1
        prompt_types = [prompt, negative_prompt]

        for idx, prompt_type in enumerate(prompt_types):
            prompt_template = None
            for prompt in prompt_type:
                if prompt_template is None:
                    prompt_template = prompt
                else:
                    assert prompt == prompt_template
            if prompt_types[idx] is not None:
                prompt_types[idx] = prompt_types[idx][0]
        prompt = prompt_types[0]
        negative_prompt = prompt_types[1]

        # Default height and width to unet
        height = height or self.unet.config.sample_size * self.vae_scale_factor
        width = width or self.unet.config.sample_size * self.vae_scale_factor

        # Check inputs. Raise error if not correct
        self.check_inputs(prompt, height, width, callback_steps)

        # Define call parameters
        batch_size = 1 if isinstance(prompt, str) else len(prompt)
        device = self._execution_device
        # here `guidance_scale` is defined analog to the guidance weight `w` of equation (2)
        # of the Imagen paper: https://arxiv.org/pdf/2205.11487.pdf . `guidance_scale = 1`
        # corresponds to doing no classifier free guidance.
        do_classifier_free_guidance = guidance_scale > 1.0

        # Encode input prompt
        text_embeddings = self._encode_prompt(
            prompt, device, num_videos_per_prompt, do_classifier_free_guidance, negative_prompt
        )

        # Prepare timesteps
        self.scheduler.set_timesteps(num_inference_steps, device=device)
        timesteps = self.scheduler.timesteps

        # print(f" Latent shape = {latents.shape}")

        # Prepare latent variables
        num_channels_latents = self.unet.in_channels

        xT = self.prepare_latents(
            batch_size * num_videos_per_prompt,
            num_channels_latents,
            1,
            height,
            width,
            text_embeddings.dtype,
            device,
            generator,
            xT,
        )
        dtype = xT.dtype

        # when motion field is not used, augment with random latent codes
        if use_motion_field:
            xT = xT[:, :, :1]
        else:
            if xT.shape[2] < video_length:
                xT_missing = self.prepare_latents(
                    batch_size * num_videos_per_prompt,
                    num_channels_latents,
                    video_length - xT.shape[2],
                    height,
                    width,
                    text_embeddings.dtype,
                    device,
                    generator,
                    None,
                )
                xT = torch.cat([xT, xT_missing], dim=2)

        xInit = xT.clone()

        timesteps_ddpm = [981, 961, 941, 921, 901, 881, 861, 841, 821, 801, 781, 761, 741, 721,
                          701, 681, 661, 641, 621, 601, 581, 561, 541, 521, 501, 481, 461, 441,
                          421, 401, 381, 361, 341, 321, 301, 281, 261, 241, 221, 201, 181, 161,
                          141, 121, 101, 81, 61, 41, 21, 1]
        timesteps_ddpm.reverse()

        t0 = timesteps_ddpm[t0]
        t1 = timesteps_ddpm[t1]

        print(f"t0 = {t0} t1 = {t1}")
        x_t1_1 = None

        # Prepare extra step kwargs.
        extra_step_kwargs = self.prepare_extra_step_kwargs(generator, eta)
        # Denoising loop
        num_warmup_steps = len(timesteps) - \
                           num_inference_steps * self.scheduler.order

        shape = (batch_size, num_channels_latents, 1, height //
                 self.vae_scale_factor, width // self.vae_scale_factor)

        ddim_res = self.DDIM_backward(num_inference_steps=num_inference_steps, timesteps=timesteps, skip_t=1000, t0=t0,
                                      t1=t1, do_classifier_free_guidance=do_classifier_free_guidance,
                                      null_embs=null_embs, text_embeddings=text_embeddings, latents_local=xT,
                                      latents_dtype=dtype, guidance_scale=guidance_scale,
                                      guidance_stop_step=guidance_stop_step,
                                      callback=callback, callback_steps=callback_steps,
                                      extra_step_kwargs=extra_step_kwargs, num_warmup_steps=num_warmup_steps)

        x0 = ddim_res["x0"].detach()

        if "x_t0_1" in ddim_res:
            x_t0_1 = ddim_res["x_t0_1"].detach()
        if "x_t1_1" in ddim_res:
            x_t1_1 = ddim_res["x_t1_1"].detach()
        del ddim_res
        del xT
        if use_motion_field:
            del x0

            x_t0_k = x_t0_1[:, :, :1, :, :].repeat(1, 1, video_length - 1, 1, 1)

            reference_flow, x_t0_k = self.create_motion_field_and_warp_latents(
                motion_field_strength_x=motion_field_strength_x, motion_field_strength_y=motion_field_strength_y,
                latents=x_t0_k, video_length=video_length, frame_ids=frame_ids[1:])

            # assuming t0=t1=1000, if t0 = 1000
            if t1 > t0:
                x_t1_k = self.DDPM_forward(
                    x0=x_t0_k, t0=t0, tMax=t1, device=device, shape=shape, text_embeddings=text_embeddings,
                    generator=generator)
            else:
                x_t1_k = x_t0_k

            if x_t1_1 is None:
                raise Exception

            x_t1 = torch.cat([x_t1_1, x_t1_k], dim=2).clone().detach()

            ddim_res = self.DDIM_backward(num_inference_steps=num_inference_steps, timesteps=timesteps, skip_t=t1,
                                          t0=-1, t1=-1, do_classifier_free_guidance=do_classifier_free_guidance,
                                          null_embs=null_embs, text_embeddings=text_embeddings, latents_local=x_t1,
                                          latents_dtype=dtype, guidance_scale=guidance_scale,
                                          guidance_stop_step=guidance_stop_step, callback=callback,
                                          callback_steps=callback_steps, extra_step_kwargs=extra_step_kwargs,
                                          num_warmup_steps=num_warmup_steps)

            x0 = ddim_res["x0"].detach()
            del ddim_res
            del x_t1
            del x_t1_1
            del x_t1_k
        else:
            x_t1 = x_t1_1.clone()
            x_t1_1 = x_t1_1[:, :, :1, :, :].clone()
            x_t1_k = x_t1_1[:, :, 1:, :, :].clone()
            x_t0_k = x_t0_1[:, :, 1:, :, :].clone()
            x_t0_1 = x_t0_1[:, :, :1, :, :].clone()

        # smooth background
        if smooth_bg:
            h, w = x0.shape[3], x0.shape[4]
            M_FG = torch.zeros((batch_size, video_length, h, w),
                               device=x0.device).to(x0.dtype)
            for batch_idx, x0_b in enumerate(x0):
                z0_b = self.decode_latents(x0_b[None]).detach()
                z0_b = rearrange(z0_b[0], "c f h w -> f h w c")
                for frame_idx, z0_f in enumerate(z0_b):
                    z0_f = torch.round(
                        z0_f * 255).cpu().numpy().astype(np.uint8)
                    # apply SOD detection
                    m_f = torch.tensor(self.sod_model.process_data(
                        z0_f), device=x0.device).to(x0.dtype)
                    mask = T.Resize(
                        size=(h, w), interpolation=T.InterpolationMode.NEAREST)(m_f[None])
                    kernel = torch.ones(5, 5, device=x0.device, dtype=x0.dtype)
                    mask = dilation(mask[None].to(x0.device), kernel)[0]
                    M_FG[batch_idx, frame_idx, :, :] = mask

            x_t1_1_fg_masked = x_t1_1 * \
                               (1 - repeat(M_FG[:, 0, :, :],
                                           "b w h -> b c 1 w h", c=x_t1_1.shape[1]))

            x_t1_1_fg_masked_moved = []
            for batch_idx, x_t1_1_fg_masked_b in enumerate(x_t1_1_fg_masked):
                x_t1_fg_masked_b = x_t1_1_fg_masked_b.clone()

                x_t1_fg_masked_b = x_t1_fg_masked_b.repeat(
                    1, video_length - 1, 1, 1)
                if use_motion_field:
                    x_t1_fg_masked_b = x_t1_fg_masked_b[None]
                    x_t1_fg_masked_b = self.warp_latents_independently(
                        x_t1_fg_masked_b, reference_flow)
                else:
                    x_t1_fg_masked_b = x_t1_fg_masked_b[None]

                x_t1_fg_masked_b = torch.cat(
                    [x_t1_1_fg_masked_b[None], x_t1_fg_masked_b], dim=2)
                x_t1_1_fg_masked_moved.append(x_t1_fg_masked_b)

            x_t1_1_fg_masked_moved = torch.cat(x_t1_1_fg_masked_moved, dim=0)

            M_FG_1 = M_FG[:, :1, :, :]

            M_FG_warped = []
            for batch_idx, m_fg_1_b in enumerate(M_FG_1):
                m_fg_1_b = m_fg_1_b[None, None]
                m_fg_b = m_fg_1_b.repeat(1, 1, video_length - 1, 1, 1)
                if use_motion_field:
                    m_fg_b = self.warp_latents_independently(
                        m_fg_b.clone(), reference_flow)
                M_FG_warped.append(
                    torch.cat([m_fg_1_b[:1, 0], m_fg_b[:1, 0]], dim=1))

            M_FG_warped = torch.cat(M_FG_warped, dim=0)

            channels = x0.shape[1]

            M_BG = (1 - M_FG) * (1 - M_FG_warped)
            M_BG = repeat(M_BG, "b f h w -> b c f h w", c=channels)
            a_convex = smooth_bg_strength

            latents = (1 - M_BG) * x_t1 + M_BG * (a_convex *
                                                  x_t1 + (1 - a_convex) * x_t1_1_fg_masked_moved)

            ddim_res = self.DDIM_backward(num_inference_steps=num_inference_steps, timesteps=timesteps, skip_t=t1,
                                          t0=-1, t1=-1, do_classifier_free_guidance=do_classifier_free_guidance,
                                          null_embs=null_embs, text_embeddings=text_embeddings, latents_local=latents,
                                          latents_dtype=dtype, guidance_scale=guidance_scale,
                                          guidance_stop_step=guidance_stop_step, callback=callback,
                                          callback_steps=callback_steps, extra_step_kwargs=extra_step_kwargs,
                                          num_warmup_steps=num_warmup_steps)
            x0 = ddim_res["x0"].detach()
            del ddim_res
            del latents

        latents = x0

        # manually for max memory savings
        if hasattr(self, "final_offload_hook") and self.final_offload_hook is not None:
            self.unet.to("cpu")
        torch.cuda.empty_cache()

        if output_type == "latent":
            image = latents
            has_nsfw_concept = None
        else:
            image = self.decode_latents(latents)

            # Run safety checker
            has_nsfw_concept = None
            image = rearrange(image, "b c f h w -> (b f) h w c")

        # Offload last model to CPU
        if hasattr(self, "final_offload_hook") and self.final_offload_hook is not None:
            self.final_offload_hook.offload()

        if not return_dict:
            return image, has_nsfw_concept

        return TextToVideoPipelineOutput(images=image, nsfw_content_detected=has_nsfw_concept)
