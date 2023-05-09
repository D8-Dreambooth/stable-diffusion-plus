# D8-Dreambooth/stable-diffusion-plus/
 Stable Diffusion + Dreambooth, without all the cruft

## What is this?
StableDiffusion+ is a completely new, from-scratch implementation of Stable Diffusion, with a focus on security, performance, and ease of use; while maintaining a more developer-friendly codebase.

The application features a modular design that allows for easy extension and modification. Existing modules include inference (image generation), Dreambooth training, a native file browser and image viewer, a tagging module, and a module for conversion of various checkpoint formats.



## Getting started

1. Ensure you have python >= 3.10 installed.
2. Clone the repository.
3. Execute launch.py using python or accelerate. For accelerated launch, run once with regular python to set up the venv, then use venv\...\accelerate

```
python launch.py
```

or

```
accelerate launch launch.py
```
4. Navigate to localhost:8080 to view the WebUI. The default username and password are both `admin`.


## Features

### Note: This list is constantly growing and changing. It is not exhaustive, nor likely up-to-date.


Diffusers-based inference with native support for ControlNet, LoRA, and dreambooth models without the need to convert/extract anything.


Mobile and PC friendly! The WebUI is designed to work on any device, and existing modules include both touch and keyboard inputs for a number of actions.


The same dreambooth training engine as used in Auto1111. Literally. It's the extension with a wrapper.


Multiple user support, with configurations to limit the number of GPU-intensive tasks allowed to run at once. Users have individual directories which are isolated from the main filesystem, as well as a shared directory for models.

A basic tagging module to allow fast captioning of images.

A native file browser and image viewer, with support for file uploads, deletions, and renaming.

