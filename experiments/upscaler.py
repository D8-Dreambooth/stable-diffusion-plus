import argparse
import glob
import os

import cv2
from PIL import Image
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from torchvision.transforms import Compose, ToTensor, Resize, ToPILImage, InterpolationMode


def main():
    """Inference demo for Real-ESRGAN.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str,
                        default="E:\\dev\\stable-diffusion-plus\\data_protected\\users\\admin\\input\\sd_db\\mj\\scale",
                        help='Input image or folder')
    parser.add_argument('-o', '--output', type=str,
                        default="E:\\dev\\stable-diffusion-plus\\data_protected\\users\\admin\\input\\sd_db\\mj\\scale_out",
                        help='Output folder')
    parser.add_argument(
        '-dn',
        '--denoise_strength',
        type=float,
        default=0.5,
        help=('Denoise strength. 0 for weak denoise (keep noise), 1 for strong denoise ability. '
              'Only used for the realesr-general-x4v3 model'))
    parser.add_argument('-s', '--outscale', type=float, default=4, help='The final upsampling scale of the image')
    parser.add_argument(
        '--model_path', type=str,
        default="E:\\dev\\stable-diffusion-plus\\data_shared\\models\\upscalers\\4xNomos8kSCSRFormer.pth",
        help='[Option] Model path. Usually, you do not need to specify it')
    parser.add_argument('--suffix', type=str, default='', help='Suffix of the restored image')
    parser.add_argument('-t', '--tile', type=int, default=0, help='Tile size, 0 for no tile during testing')
    parser.add_argument('--tile_pad', type=int, default=10, help='Tile padding')
    parser.add_argument('--pre_pad', type=int, default=0, help='Pre padding size at each border')
    parser.add_argument('--face_enhance', action='store_true', help='Use GFPGAN to enhance face')
    parser.add_argument(
        '--fp32', action='store_true', help='Use fp32 precision during inference. Default: fp16 (half precision).')
    parser.add_argument(
        '--alpha_upsampler',
        type=str,
        default='realesrgan',
        help='The upsampler for the alpha channels. Options: realesrgan | bicubic')
    parser.add_argument(
        '--ext',
        type=str,
        default='auto',
        help='Image extension. Options: auto | jpg | png, auto means using the same extension as inputs')
    parser.add_argument(
        '-g', '--gpu-id', type=int, default=None, help='gpu device to use (default=None) can be 0,1,2 for multi-gpu')

    args = parser.parse_args()

    # determine model paths
    model_path = args.model_path

    # use dni to control the denoise strength
    dni_weight = None
    # restorer
    print(f"Loading model from {model_path}.")
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    netscale = 4
    # Restorer Class
    upsampler = RealESRGANer(
        scale=netscale,
        model_path=model_path,
        dni_weight=None,
        model=model,
        tile=128,
        tile_pad=10,
        pre_pad=10,
        half=False,
        gpu_id=None,
    )

    os.makedirs(args.output, exist_ok=True)

    if os.path.isfile(args.input):
        paths = [args.input]
    else:
        paths = sorted(glob.glob(os.path.join(args.input, '*')))

    for idx, path in enumerate(paths):
        imgname, extension = os.path.splitext(os.path.basename(path))
        print('Testing', idx, imgname)

        try:
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if len(img.shape) == 3 and img.shape[2] == 4:
                img_mode = 'RGBA'
            else:
                img_mode = None
        except Exception as error:
            print('Failed to load image', path)
            print('Error', error)
            continue
        # if the image's largest dimension is greater than 2048, just copy it to the output folder
        if max(img.shape) > 2048:
            copy_path = os.path.join(args.output, os.path.basename(path))
            cv2.imwrite(copy_path, img)

        try:
            output, _ = upsampler.enhance(img, outscale=args.outscale)
        except RuntimeError as error:
            print('Error', error)
            print('If you encounter CUDA out of memory, try to set --tile with a smaller number.')
        else:
            if args.ext == 'auto':
                extension = extension[1:]
            else:
                extension = args.ext
            if img_mode == 'RGBA':  # RGBA images should be saved in png format
                extension = 'png'
            if args.suffix == '':
                save_path = os.path.join(args.output, f'{imgname}.{extension}')
            else:
                save_path = os.path.join(args.output, f'{imgname}_{args.suffix}.{extension}')
            cv2.imwrite(save_path, output)


if __name__ == '__main__':
    main()


def process_images(directory, model):
    # list all files in directory
    files = os.listdir(directory)

    # filter list down to only images
    images = [file for file in files if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))]

    # compose transformation (upscale using model, then downscale using lanczos)
    transform = Compose([
        ToTensor(),
        lambda x: model(x.unsqueeze(0)),
        ToPILImage(),
        Resize((4096, 4096), interpolation=InterpolationMode.LANCZOS),
    ])

    # iterate through each image
    for image in images:
        # open image
        with Image.open(os.path.join(directory, image)) as img:
            # apply transformations
            result = transform(img)
            result.save(os.path.join(directory, 'processed_' + image))


if __name__ == "__main__":
    main()
