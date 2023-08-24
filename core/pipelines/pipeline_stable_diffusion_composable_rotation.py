"""
    modified based on diffusion library from Huggingface: https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/stable_diffusion/pipeline_stable_diffusion.py
"""
import inspect
import logging
import warnings
from typing import List, Optional, Union

import torch
from diffusers.models import AutoencoderKL, UNet2DConditionModel
from diffusers.pipeline_utils import DiffusionPipeline
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker, StableDiffusionPipelineOutput
from diffusers.schedulers import DDIMScheduler, LMSDiscreteScheduler, PNDMScheduler
from transformers import CLIPFeatureExtractor, CLIPTextModel, CLIPTokenizer

from core.pipelines.pipeline_optim_mixin import PipelineOptimMixin


def get_prependicualr_component(x, y):
    assert x.shape == y.shape
    # print(((torch.mul(x, y).sum())/(torch.norm(y)**2)).shape)
    return x - ((torch.mul(x, y).sum()) / (torch.norm(y) ** 2)) * y


def weighted_prependicualr_aggricator(delta_noise_pred_pos, w_pos, delta_noise_pred_neg, w_neg):
    main_positive = delta_noise_pred_pos[0].unsqueeze(0)
    accumulated_output = 0
    for i, complementory_positive in enumerate(delta_noise_pred_pos[1:]):
        accumulated_output += w_pos[i] * get_prependicualr_component(complementory_positive.unsqueeze(0), main_positive)

    for i, w_n in enumerate(w_neg):
        accumulated_output -= w_n * get_prependicualr_component(delta_noise_pred_neg[i].unsqueeze(0), main_positive)

    return accumulated_output + main_positive


class StableDiffusionComposableRotationPipeline(DiffusionPipeline, PipelineOptimMixin):
    r"""
    Pipeline for text-to-image generation using Stable Diffusion.

    This model inherits from [`DiffusionPipeline`]. Check the superclass documentation for the generic methods the
    library implements for all the pipelines (such as downloading or saving, running on a particular device, etc.)

    Args:
        vae ([`AutoencoderKL`]):
            Variational Auto-Encoder (VAE) Model to encode and decode images to and from latent representations.
        text_encoder ([`CLIPTextModel`]):
            Frozen text-encoder. Stable Diffusion uses the text portion of
            [CLIP](https://huggingface.co/docs/transformers/model_doc/clip#transformers.CLIPTextModel), specifically
            the [clip-vit-large-patch14](https://huggingface.co/openai/clip-vit-large-patch14) variant.
        tokenizer (`CLIPTokenizer`):
            Tokenizer of class
            [CLIPTokenizer](https://huggingface.co/docs/transformers/v4.21.0/en/model_doc/clip#transformers.CLIPTokenizer).
        unet ([`UNet2DConditionModel`]): Conditional U-Net architecture to denoise the encoded image latents.
        scheduler ([`SchedulerMixin`]):
            A scheduler to be used in combination with `unet` to denoise the encoded image latens. Can be one of
            [`DDIMScheduler`], [`LMSDiscreteScheduler`], or [`PNDMScheduler`].
        safety_checker ([`StableDiffusionSafetyChecker`]):
            Classification module that estimates whether generated images could be considered offsensive or harmful.
            Please, refer to the [model card](https://huggingface.co/CompVis/stable-diffusion-v1-4) for details.
        feature_extractor ([`CLIPFeatureExtractor`]):
            Model that extracts features from generated images to be used as inputs for the `safety_checker`.
    """

    _optional_components = ["safety_checker", "feature_extractor"]

    def __init__(
            self,
            vae: AutoencoderKL,
            text_encoder: CLIPTextModel,
            tokenizer: CLIPTokenizer,
            unet: UNet2DConditionModel,
            scheduler: Union[DDIMScheduler, PNDMScheduler, LMSDiscreteScheduler],
            safety_checker: StableDiffusionSafetyChecker,
            feature_extractor: CLIPFeatureExtractor,
    ):
        super().__init__()
        # scheduler = scheduler.set_format("pt")
        self.register_modules(
            vae=vae,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            unet=unet,
            scheduler=scheduler,
            safety_checker=safety_checker,
            feature_extractor=feature_extractor,
        )

    def enable_attention_slicing(self, slice_size: Optional[Union[str, int]] = "auto"):
        r"""
        Enable sliced attention computation.

        When this option is enabled, the attention module will split the input tensor in slices, to compute attention
        in several steps. This is useful to save some memory in exchange for a small speed decrease.

        Args:
            slice_size (`str` or `int`, *optional*, defaults to `"auto"`):
                When `"auto"`, halves the input to the attention heads, so attention will be computed in two steps. If
                a number is provided, uses as many slices as `attention_head_dim // slice_size`. In this case,
                `attention_head_dim` must be a multiple of `slice_size`.
        """
        if slice_size == "auto":
            # half the attention head size is usually a good trade-off between
            # speed and memory
            slice_size = self.unet.config.attention_head_dim // 2
        self.unet.set_attention_slice(slice_size)

    def disable_attention_slicing(self):
        r"""
        Disable sliced attention computation. If `enable_attention_slicing` was previously invoked, this method will go
        back to computing attention in one step.
        """
        # set slice_size = `None` to disable `attention slicing`
        self.enable_attention_slicing(None)

    @torch.no_grad()
    def __call__(
            self,
            prompt: Union[str, List[str]],
            combined_w: Union[float, List[float]] = 0.5,
            height: Optional[int] = 512,
            width: Optional[int] = 512,
            num_inference_steps: Optional[int] = 50,
            guidance_scale: Optional[float] = 7.5,
            eta: Optional[float] = 0.0,
            generator: Optional[torch.Generator] = None,
            latents: Optional[torch.FloatTensor] = None,
            output_type: Optional[str] = "pil",
            return_dict: bool = True,
            weights: Optional[str] = "",
            **kwargs,
    ):
        r"""
        Function invoked when calling the pipeline for generation.

        Args:
            prompt (`str` or `List[str]`):
                The prompt or prompts to guide the image generation.
            height (`int`, *optional*, defaults to 512):
                The height in pixels of the generated image.
            width (`int`, *optional*, defaults to 512):
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
            eta (`float`, *optional*, defaults to 0.0):
                Corresponds to parameter eta (η) in the DDIM paper: https://arxiv.org/abs/2010.02502. Only applies to
                [`schedulers.DDIMScheduler`], will be ignored for others.
            generator (`torch.Generator`, *optional*):
                A [torch generator](https://pytorch.org/docs/stable/generated/torch.Generator.html) to make generation
                deterministic.
            latents (`torch.FloatTensor`, *optional*):
                Pre-generated noisy latents, sampled from a Gaussian distribution, to be used as inputs for image
                generation. Can be used to tweak the same generation with different prompts. If not provided, a latents
                tensor will ge generated by sampling using the supplied random `generator`.
            output_type (`str`, *optional*, defaults to `"pil"`):
                The output format of the generate image. Choose between
                [PIL](https://pillow.readthedocs.io/en/stable/): `PIL.Image.Image` or `nd.array`.
            return_dict (`bool`, *optional*, defaults to `True`):
                Whether or not to return a [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] instead of a
                plain tuple.

        Returns:
            [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] or `tuple`:
            [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] if `return_dict` is True, otherwise a `tuple.
            When returning a tuple, the first element is a list with the generated images, and the second element is a
            list of `bool`s denoting whether the corresponding generated image likely represents "not-safe-for-work"
            (nsfw) content, according to the `safety_checker`.
        """

        if "torch_device" in kwargs:
            device = kwargs.pop("torch_device")
            warnings.warn(
                "`torch_device` is deprecated as an input argument to `__call__` and will be removed in v0.3.0."
                " Consider using `pipe.to(torch_device)` instead."
            )

            # Set device as before (to be removed in 0.3.0)
            if device is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"
            self.to(device)

        if isinstance(prompt, str):
            batch_size = 1
        elif isinstance(prompt, list):
            batch_size = len(prompt)
        else:
            raise ValueError(f"`prompt` has to be of type `str` or `list` but is {type(prompt)}")

        if height % 8 != 0 or width % 8 != 0:
            raise ValueError(f"`height` and `width` have to be divisible by 8 but are {height} and {width}.")

        if isinstance(prompt, str):
            if '|' in prompt:
                prompt = [x.strip() for x in prompt.split('|')]
                print(f"composing {prompt}...")
            else:
                prompt = [prompt]

        elif isinstance(prompt, list):
            prompt_parts = []
            for p in prompt:
                if '|' in p:
                    prompt_parts.extend([x.strip() for x in p.split('|')])
                else:
                    prompt_parts.append(p)
            prompt = prompt_parts
        logging.getLogger(__name__).debug(f"Prompt: {prompt}")
        # get prompt text embeddings
        text_input = self.tokenizer(
            prompt,
            padding="max_length",
            max_length=self.tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        )
        num_prompts = len(prompt)  # calculate the number of prompts before combining

        text_embeddings = self.text_encoder(text_input.input_ids.to(self.device))[0]
        print(text_embeddings.shape)
        text_embeddings = combined_w * text_embeddings[0].unsqueeze(0) + (1 - combined_w) * text_embeddings[
            1].unsqueeze(0)
        print(text_embeddings.shape)

        if not weights:
            weight_dist = 1 / text_embeddings.shape[0]
            weights = "|".join([f"{weight_dist}"] * text_embeddings.shape[0])
        weights = [float(w.strip()) for w in weights.split("|")]
        weights = torch.tensor(weights, device=self.device)
        assert len(weights) == text_embeddings.shape[0], "weights specified are not equal to the number of prompts"
        pos_weights = []
        neg_weights = []
        mask = []  # first one is unconditional score
        for w in weights:
            if w > 0:
                pos_weights.append(w)
                mask.append(True)
            else:
                neg_weights.append(abs(w))
                mask.append(False)
        # normalize the weights
        pos_weights = torch.tensor(pos_weights, device=self.device).reshape(-1, 1, 1, 1)
        neg_weights = torch.tensor(neg_weights, device=self.device).reshape(-1, 1, 1, 1)
        mask = torch.tensor(mask, device=self.device, dtype=torch.bool)

        # here `guidance_scale` is defined analog to the guidance weight `w` of equation (2)
        # of the Imagen paper: https://arxiv.org/pdf/2205.11487.pdf . `guidance_scale = 1`
        # corresponds to doing no classifier free guidance.
        do_classifier_free_guidance = guidance_scale > 1.0
        # get unconditional embeddings for classifier free guidance
        # if do_classifier_free_guidance:
        max_length = text_input.input_ids.shape[-1]

        uncond_input = self.tokenizer(
            [""] * 1, padding="max_length", max_length=max_length, return_tensors="pt"
        )
        uncond_embeddings = self.text_encoder(uncond_input.input_ids.to(self.device))[0]

        latents_device = "cpu" if self.device.type == "mps" else self.device
        latents_shape = (batch_size, self.unet.in_channels, height // 8, width // 8)
        if latents is None:
            latents = torch.randn(
                latents_shape,
                generator=generator,
                device=latents_device,
            )
        else:
            if latents.shape != latents_shape:
                raise ValueError(f"Unexpected latents shape, got {latents.shape}, expected {latents_shape}")
        latents = latents.to(self.device)

        # set timesteps
        accepts_offset = "offset" in set(inspect.signature(self.scheduler.set_timesteps).parameters.keys())
        extra_set_kwargs = {}
        if accepts_offset:
            extra_set_kwargs["offset"] = 1

        self.scheduler.set_timesteps(num_inference_steps, **extra_set_kwargs)

        # if we use LMSDiscreteScheduler, let's make sure latents are mulitplied by sigmas
        if isinstance(self.scheduler, LMSDiscreteScheduler):
            latents = latents * self.scheduler.sigmas[0]

        # prepare extra kwargs for the scheduler step, since not all schedulers have the same signature
        # eta (η) is only used with the DDIMScheduler, it will be ignored for other schedulers.
        # eta corresponds to η in DDIM paper: https://arxiv.org/abs/2010.02502
        # and should be between [0, 1]
        accepts_eta = "eta" in set(inspect.signature(self.scheduler.step).parameters.keys())
        extra_step_kwargs = {}
        if accepts_eta:
            extra_step_kwargs["eta"] = eta

        for i, t in enumerate(self.progress_bar(self.scheduler.timesteps)):
            # expand the latents if we are doing classifier free guidance
            latent_model_input = torch.cat(
                [latents] * text_embeddings.shape[0]) if do_classifier_free_guidance else latents
            if isinstance(self.scheduler, LMSDiscreteScheduler):
                sigma = self.scheduler.sigmas[i]
                # the model input needs to be scaled to match the continuous ODE formulation in K-LMS
                latent_model_input = latent_model_input / ((sigma ** 2 + 1) ** 0.5)

            # reduce memory by predicting each score sequentially
            noise_preds = []
            # Get the weight_dtype from the unet model
            weight_dtype = torch.float16

            # predict the noise residual
            for latent_in, text_embedding_in in zip(
                    torch.chunk(latent_model_input, chunks=latent_model_input.shape[0], dim=0),
                    torch.chunk(text_embeddings, chunks=text_embeddings.shape[0], dim=0)):

                # Cast the latent_in to the same type as the model's weights
                latent_in = latent_in.to(weight_dtype)
                noise_preds.append(self.unet(latent_in, t, encoder_hidden_states=text_embedding_in).sample)
            noise_preds = torch.cat(noise_preds, dim=0)
            latents = latents.to(weight_dtype)
            noise_pred_uncond = self.unet(latents, t, encoder_hidden_states=uncond_embeddings).sample

            # perform guidance
            if do_classifier_free_guidance:
                # Then use the expanded mask for indexing
                delta_noise_pred_neg = noise_preds[~mask] - noise_pred_uncond
                delta_noise_pred_pos = noise_preds[mask] - noise_pred_uncond

                noise_pred = noise_pred_uncond + guidance_scale * weighted_prependicualr_aggricator(
                    delta_noise_pred_pos, pos_weights, delta_noise_pred_neg, neg_weights)

            # compute the previous noisy sample x_t -> x_t-1
            if isinstance(self.scheduler, LMSDiscreteScheduler):
                latents = self.scheduler.step(noise_pred, i, latents, **extra_step_kwargs).prev_sample
            else:
                latents = self.scheduler.step(noise_pred, t, latents, **extra_step_kwargs).prev_sample

        # scale and decode the image latents with vae
        latents = 1 / 0.18215 * latents
        image = self.vae.decode(latents).sample

        image = (image / 2 + 0.5).clamp(0, 1)
        image = image.cpu().permute(0, 2, 3, 1).numpy()

        has_nsfw_concept = [False for i in range(image.shape[0])]

        if output_type == "pil":
            image = self.numpy_to_pil(image)

        if not return_dict:
            return image, has_nsfw_concept
        logging.getLogger(__name__).debug(f"Generated {len(image)} images")
        return StableDiffusionPipelineOutput(images=image, nsfw_content_detected=has_nsfw_concept)