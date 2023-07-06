def apply_lora(pipeline, checkpoint_path, alpha=0.75):
    lora_prefix_unet = "lora_unet"
    lora_prefix_text_encoder = "lora_te"
    state_dict = load_file(checkpoint_path)
    visited = []
    errors = 0
    total = 0
    bad_keys = []
    # directly update weight in diffusers model
    for key in state_dict:
        # key fromat
        # 'lora_unet_down_blocks_0_attentions_1_transformer_blocks_0_attn1_to_out_0.alpha'
        # 'lora_unet_down_blocks_0_attentions_1_transformer_blocks_0_attn1_to_out_0.lora_down.weight'
        # 'lora_unet_down_blocks_0_attentions_1_transformer_blocks_0_attn1_to_out_0.lora_up.weight'

        # alpha will handled, continue for skip
        if ".alpha" in key or key in visited:
            continue

        if "text" in key:
            layer_infos = key.split(".")[0].split(self.lora_prefix_text_encoder_name + "_")[-1].split("_")
            curr_layer = self.text_encoder
            dtype = self.text_encoder.dtype
        else:
            layer_infos = key.split(".")[0].split(self.lora_prefix_unet_name + "_")[-1].split("_")
            curr_layer = self.unet
            dtype = self.unet.dtype

        # traverse layer_infos to find the key-specific layer
        temp_name = layer_infos.pop(0)
        while len(layer_infos) > -1:
            try:
                curr_layer = curr_layer.__getattr__(temp_name)
                if len(layer_infos) > 0:
                    temp_name = layer_infos.pop(0)
                elif len(layer_infos) == 0:
                    break
            except Exception:
                if len(temp_name) > 0:
                    temp_name += "_" + layer_infos.pop(0)
                else:
                    temp_name = layer_infos.pop(0)

        layer_keys = [key.split(".", 1)[0] + v for v in [".lora_up.weight", ".lora_down.weight", ".alpha"]]

        weight_up = state_dict[layer_keys[0]].to(dtype)
        weight_down = state_dict[layer_keys[1]].to(dtype)
        alpha = state_dict[layer_keys[2]]
        alpha = alpha.item() / weight_up.shape[1] if alpha else 1.0

        # update weights
        if len(state_dict[layer_keys[0]].shape) == 4:
            weight_up = weight_up.squeeze(3).squeeze(2)
            weight_down = weight_down.squeeze(3).squeeze(2)
            curr_layer.weight.data += weight * alpha * torch.mm(weight_up, weight_down).unsqueeze(2).unsqueeze(3)
        else:
            curr_layer.weight.data += weight * alpha * torch.mm(weight_up, weight_down)

        # update visited list
        for item in layer_keys:
            visited.append(item)