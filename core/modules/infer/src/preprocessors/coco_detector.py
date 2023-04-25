import PIL.Image
import numpy as np
import torch
import torchvision
from torchvision import transforms
from torchvision.models.segmentation import FCN_ResNet101_Weights


class CocoDetector(object):

    def __init__(self):
        # Create the Processor and load the model.
        self.processor = torchvision.models.segmentation.fcn_resnet101(weights=FCN_ResNet101_Weights.DEFAULT).eval()
        self.transform = transforms.Compose([
            transforms.Resize(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def __call__(self, image: PIL.Image.Image):
        og_size = image.size
        # Preprocess the image for segmentation
        image = self.transform(image)

        # Detect the various elements in the image
        with torch.no_grad():
            prediction = self.processor(image.unsqueeze(0))

        # Extract the tensor from the ordered dict
        out = prediction['out']
        om = torch.argmax(out.squeeze(), dim=0).detach().cpu().numpy()
        n_dim = out.shape[2]
        segmentation_map = self.decode_segmap(om, n_dim)

        # Resize the segmentation map to the original size of the input image
        segmentation_map = segmentation_map.resize((og_size[0], og_size[1]), resample=PIL.Image.LANCZOS)

        # Return a PIL image of the resulting segmentation map
        return segmentation_map

    @staticmethod
    def decode_segmap(image, nc=21):
        # Generate random colors to use for each class label
        label_colors = np.random.randint(0, 255, size=(nc, 3), dtype=np.uint8)
        label_colors[0] = [0, 0, 0]
        # Convert the segmentation map to a colored image
        r = np.zeros_like(image).astype(np.uint8)
        g = np.zeros_like(image).astype(np.uint8)
        b = np.zeros_like(image).astype(np.uint8)

        for l in range(0, nc):
            idx = image == l
            r[idx] = label_colors[l, 0]
            g[idx] = label_colors[l, 1]
            b[idx] = label_colors[l, 2]

        rgb = np.stack([r, g, b], axis=2)

        # Convert the numpy array to a PIL Image
        rgb = PIL.Image.fromarray(rgb)

        return rgb
