import logging
import os
import re
import shutil

import torch
import tqdm
from safetensors.torch import load_file, save_file

from core.dataclasses.model_data import ModelData
from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler

logger = logging.getLogger(__name__)
checkpoint_dict_skip_on_merge = ["text_model.embeddings.position_ids"]


def to_half(tensor, enable):
    if enable and tensor.dtype == torch.float:
        return tensor.half()

    return tensor


class ModelMerge:
    def __init__(self, user_name):
        self.status_handler = StatusHandler(user_name=user_name, target="import_export")
        self.model_handler = ModelHandler(user_name=user_name)

    def merge(self,
              merge_new_name: str,
              primary_model: ModelData,
              secondary_model: ModelData,
              tertiary_model: ModelData = None,
              merge_type: str = "weighted_sum",
              merge_multiplier: float = 0.5,
              save_as_half: bool = False,
              discard_weights: bool = False):
        """

        :param primary_model:
        :param secondary_model:
        :param tertiary_model:
        :param merge_type: One of "weighted_sum", "add_difference", or "no_interpolation"
        :param merge_multiplier:
        :param save_as_half:
        :param merge_new_name:
        :param discard_weights:
        :return:
        """
        self.status_handler.start("Beginning model merge.")

        def fail(message):
            logger.error(message)
            self.status_handler.update("status", message)
            self.status_handler.end(message)
            return {"name": "status", "message": message, }

        def weighted_sum(theta0, theta1, alpha):
            return ((1 - alpha) * theta0) + (alpha * theta1)

        def get_difference(theta1, theta2):
            return theta1 - theta2

        def add_difference(theta0, theta1_2_diff, alpha):
            return theta0 + (alpha * theta1_2_diff)

        def filename_weighted_sum():
            a = primary_model.name
            b = secondary_model.name
            Ma = round(1 - merge_multiplier, 2)
            Mb = round(merge_multiplier, 2)

            return f"{Ma}({a}) + {Mb}({b})"

        def filename_add_difference():
            a = primary_model.name
            b = secondary_model.name
            c = tertiary_model.name
            M = round(merge_multiplier, 2)

            return f"{a} + {M}({b} - {c})"

        def filename_nothing():
            return primary_model.name

        theta_funcs = {
            "weighted_sum": (filename_weighted_sum, None, weighted_sum),
            "add_difference": (filename_add_difference, get_difference, add_difference),
            "no_interpolation": (filename_nothing, None, None),
        }
        filename_generator, theta_func1, theta_func2 = theta_funcs[merge_type]
        self.status_handler.update("progress_1_total", (1 if theta_func1 else 0) + (1 if theta_func2 else 0))

        if theta_func2 and not secondary_model:
            return fail("Failed: Merging requires a secondary model.")

        if theta_func1 and not tertiary_model:
            return fail(f"Failed: Interpolation method ({merge_type}) requires a tertiary model.")

        result_is_inpainting_model = False
        result_is_instruct_pix2pix_model = False

        if theta_func2:
            self.status_handler.update("status", f"Loading B")
            logger.debug(f"Loading {secondary_model.display_name}...")
            theta_1_unet_path = os.path.join(secondary_model.path, "unet", "diffusion_pytorch_model.safetensors")
            theta_1_tenc_path = os.path.join(secondary_model.path, "text_encoder", "model.safetensors")
            theta_1_unet = load_file(theta_1_unet_path, device='cpu')
            theta_1_tenc = load_file(theta_1_tenc_path, device='cpu')
        else:
            theta_1_unet = None
            theta_1_tenc = None

        if theta_func1:
            self.status_handler.update("status", f"Loading C")
            logger.debug(f"Loading {tertiary_model.display_name}...")
            theta_2_unet_path = os.path.join(tertiary_model.path, "unet", "diffusion_pytorch_model.safetensors")
            theta_2_tenc_path = os.path.join(tertiary_model.path, "text_encoder", "model.safetensors")
            theta_2_unet = load_file(theta_2_unet_path, device='cpu')
            theta_2_tenc = load_file(theta_2_tenc_path, device='cpu')
            total_keys = len(theta_2_unet.keys()) + len(theta_2_tenc.keys())
            self.status_handler.update(
                items={"status": "Merging B and C", "progress_1_total": total_keys, "progress_1_current": 0})
            for src, dest in [(theta_2_unet, theta_1_unet), (theta_2_tenc, theta_1_tenc)]:
                for key in tqdm.tqdm(dest.keys()):
                    if key in checkpoint_dict_skip_on_merge:
                        continue

                    if 'model' in key:
                        if key in src:
                            t2 = src.get(key, torch.zeros_like(dest[key]))
                            dest[key] = theta_func1(dest[key], t2)
                        else:
                            dest[key] = torch.zeros_like(dest[key])

                    self.status_handler.step()
                del src

        self.status_handler.update("status", f"Loading {primary_model.display_name}...")
        theta_0_unet_path = os.path.join(primary_model.path, "unet", "diffusion_pytorch_model.safetensors")
        theta_0_tenc_path = os.path.join(primary_model.path, "text_encoder", "model.safetensors")
        theta_0_unet = load_file(theta_0_unet_path, device='cpu')
        theta_0_tenc = load_file(theta_0_tenc_path, device='cpu')

        logger.debug("Merging...")
        total_keys = len(theta_0_unet.keys()) + len(theta_0_tenc.keys())
        self.status_handler.update(
            items={"status": "Merging A and B", "progress_1_total": total_keys, "progress_1_current": 0})
        for theta_0, theta_1 in [(theta_0_unet, theta_1_unet), (theta_0_tenc, theta_1_tenc)]:
            for key in tqdm.tqdm(theta_0.keys()):
                if theta_1 and 'model' in key and key in theta_1:

                    if key in checkpoint_dict_skip_on_merge:
                        continue
                    logger.debug(f"Checking key {key}")
                    a = theta_0[key]
                    b = theta_1[key]

                    # this enables merging an inpainting model (A) with another one (B);
                    # where normal model would have 4 channels, for latenst space, inpainting model would
                    # have another 4 channels for unmasked picture's latent space, plus one channel for mask, for a total of 9
                    if a.shape != b.shape and a.shape[0:1] + a.shape[2:] == b.shape[0:1] + b.shape[2:]:
                        if a.shape[1] == 4 and b.shape[1] == 9:
                            raise RuntimeError(
                                "When merging inpainting model with a normal one, A must be the inpainting model.")
                        if a.shape[1] == 4 and b.shape[1] == 8:
                            raise RuntimeError(
                                "When merging instruct-pix2pix model with a normal one, A must be the instruct-pix2pix model.")

                        if a.shape[1] == 8 and b.shape[1] == 4:  # If we have an Instruct-Pix2Pix model...
                            theta_0[key][:, 0:4, :, :] = theta_func2(a[:, 0:4, :, :], b,
                                                                     merge_multiplier)  # Merge only the vectors the models have in common.  Otherwise we get an error due to dimension mismatch.
                            result_is_instruct_pix2pix_model = True
                        else:
                            assert a.shape[1] == 9 and b.shape[
                                1] == 4, f"Bad dimensions for merged layer {key}: A={a.shape}, B={b.shape}"
                            theta_0[key][:, 0:4, :, :] = theta_func2(a[:, 0:4, :, :], b, merge_multiplier)
                            result_is_inpainting_model = True
                    else:
                        theta_0[key] = theta_func2(a, b, merge_multiplier)

                    theta_0[key] = to_half(theta_0[key], save_as_half)
                else:
                    logger.debug(f"Skipping key {key}")
                self.status_handler.step()
            del theta_1

        if save_as_half and not theta_func2:
            for theta_0 in [theta_0_unet, theta_0_tenc]:
                for key in theta_0.keys():
                    theta_0[key] = to_half(theta_0[key], save_as_half)

                if discard_weights:
                    regex = re.compile(discard_weights)
                    for key in list(theta_0):
                        if re.search(regex, key):
                            theta_0.pop(key, None)

        filename = merge_new_name
        filename += "_inpainting" if result_is_inpainting_model else ""
        filename += "_instruct-pix2pix" if result_is_instruct_pix2pix_model else ""
        model_dir = self.model_handler.user_path
        out_file = os.path.join(model_dir, "diffusers", filename)

        self.status_handler.update("status", "Saving")
        logger.debug(f"Saving to {out_file}...")
        src_path = primary_model.path
        for src_dir in os.listdir(src_path):
            src_dir = os.path.join(src_path, src_dir)
            if os.path.isdir(src_dir):
                dest_dir = os.path.join(out_file, os.path.basename(src_dir))
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                if "unet" in src_dir or "text_encoder" in src_dir:
                    tgt_file = os.path.join(src_dir, "config.json")
                    dest_file = os.path.join(dest_dir, "config.json")
                    if not os.path.exists(dest_file):
                        shutil.copy(tgt_file, dest_file)
                else:
                    for filename in os.listdir(src_dir):
                        file = os.path.join(src_dir, filename)
                        dest_file = os.path.join(dest_dir, filename)
                        if os.path.isfile(file) and not os.path.exists(dest_file):
                            shutil.copy(file, dest_file)
        index = os.path.join(src_path, "model_index.json")
        if os.path.exists(index):
            shutil.copy(index, os.path.join(out_file, "model_index.json"))
        out_unet = os.path.join(out_file, "unet", "diffusion_pytorch_model.safetensors")
        out_tenc = os.path.join(out_file, "text_encoder", "model.safetensors")
        if not os.path.exists(os.path.join(out_file, "unet")):
            os.makedirs(os.path.join(out_file, "unet"))
        if not os.path.exists(os.path.join(out_file, "text_encoder")):
            os.makedirs(os.path.join(out_file, "text_encoder"))
        save_file(theta_0_unet, out_unet, metadata={"format": "pt"})
        save_file(theta_0_tenc, out_tenc, metadata={"format": "pt"})
        logger.debug(f"Saved to {out_file}.")
        self.model_handler.refresh("diffusers")
        self.status_handler.end("Checkpoint saved.")
        return {"status": "success", "message": "Checkpoint saved."}
