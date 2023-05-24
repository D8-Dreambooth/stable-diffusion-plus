import os

from core.handlers.directories import DirectoryHandler

checkpoint_file = "https://huggingface.co/lllyasviel/ControlNet/resolve/main/annotator/ckpts/upernet_global_small.pth"


class UniformerDetector:
    def __init__(self):
        """
        Initializes the ControlNet class.
        Loads the upernet_global_small.pth model from the specified directory.
        If the model does not exist, downloads it from the URL specified in checkpoint_file.
        Loads the configuration file for the model.
        Initializes the segmentor with the configuration file and model path.
        Moves the model to the GPU.
        @param: None
        @return: None
        """
        dh = DirectoryHandler()
        models_dir = os.path.join(dh.shared_path, "models", "controlnet")
        modelpath = os.path.join(models_dir, "upernet_global_small.pth")
        if not os.path.exists(modelpath):
            from basicsr.utils.download_util import load_file_from_url
            load_file_from_url(checkpoint_file, model_dir=models_dir)
        config_file = os.path.join(os.path.dirname(models_dir), "uniformer", "exp", "upernet_global_small", "config.py")
        self.model = init_segmentor(config_file, modelpath).cuda()

    def __call__(self, img):
        """
        Runs the ControlNet model on the input image and returns the resulting segmented image.
        Displays the resulting segmented image with the specified palette and opacity.
        @param img: PIL.Image
        @return: PIL.Image
        """
        result = inference_segmentor(self.model, img)
        res_img = show_result_pyplot(self.model, img, result, get_palette('ade'), opacity=1)
        return res_img