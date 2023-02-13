<h1>Stable-Diffusion Plus</h1>


<p>
This project uses <a href="https://fastapi.tiangolo.com/">FastAPI</a>, <a href="https://jinja.palletsprojects.com/en/2.11.x/">Jinja2</a>, and <a href="https://getbootstrap.com/docs/4.1/getting-started/introduction/">Bootstrap4</a>.
</p>



## Python environment

3.10

## Requirements

```sh
accelerate>=0.16.0
albumentations>=1.3.0
bitsandbytes==0.35.4
diffusers>=0.12.1
fastapi>=0.91.0
ftfy>=6.1.1
modelcards>=0.1.6
tensorboard>=2.12.0
tensorflow>=2.11.0; sys_platform != 'darwin' or platform_machine != 'arm64'
tensorflow-macos>=2.11.0; sys_platform >= 'darwin' and platform_machine >= 'arm64'
torch>=1.13.1
torchvision>=0.14.1
tqdm>=4.64.1
transformers>=4.26.1
discord-webhook>=1.0.0
xformers==0.0.17.dev447
```
