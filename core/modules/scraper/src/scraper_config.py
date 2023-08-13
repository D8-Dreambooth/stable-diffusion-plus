import json
from typing import Optional, List
from pydantic import BaseModel, Field

from core.modules.scraper.src.gid_tables import COLOR_TABLE, SIZE_TABLE, TYPE_TABLE, TIME_TABLE, ASPECT_RATIO_TABLE, \
    LICENSE_TABLE


class ScraperConfig(BaseModel):
    keywords: Optional[str] = Field(title="Keywords", default="", description="A comma separated list of keywords")
    exact_words: Optional[str] = Field(title="Exact Words", description="A comma separated list of exact words")
    any_words: Optional[str] = Field(title="Any Words", description="A comma separated list of any words")
    exclude_words: Optional[str] = Field(title="Exclude Words", description="A comma separated list of words to exclude")
    limit: int = Field(100, title="Max Images", description="Number of images to download", ge=1, le=10000)
    color: Optional[str] = Field(None, description="Filter on color", title="Color Filter",
                                 choices=[key for key in COLOR_TABLE.keys()])
    size: str = Field("large", description="Image size", title="Image Size",
                      choices=[key for key in SIZE_TABLE.keys()])
    type: Optional[str] = Field(None, description="Image type", title="Image Type",
                                choices=[key for key in TYPE_TABLE.keys()])
    time: Optional[str] = Field(None, description="Image age", title="Image Age",
                                choices=[key for key in TIME_TABLE.keys()])
    usage: Optional[str] = Field(None, description="Image usage rights", title="Usage Rights", choices=[key for key in LICENSE_TABLE.keys()])
    aspect_ratio: Optional[str] = Field(None, description="Comma separated additional words added to keywords",
                                        choices=[key for key in ASPECT_RATIO_TABLE.keys()], title="Aspect Ratio")
    browser: str = Field("chrome", description="Specify which browser to use",
                         choices=['chrome', 'chromium', 'brave', 'firefox', 'safari', 'ie', 'edge', 'opera'],
                         title="Browser")
    related_images: bool = Field(False, description="Downloads images that are similar to the keyword provided", title="Related Images")

    def get_params(self):
        tc_fields = {}
        keys = []
        for f, data in self.__fields__.items():
            value = getattr(self, f)
            try:
                json.dumps(value)
            except TypeError:
                continue
            field_dict = {}

            for prop in ['default', 'description', 'title', 'ge', 'le', 'gt', 'lt', 'multiple_of']:
                if hasattr(data.field_info, prop):
                    value = getattr(data.field_info, prop)
                    # Check if the property is JSON serializable
                    if value is None:
                        continue
                    try:
                        json.dumps(value)
                        if prop == "ge":
                            prop = "min"
                        elif prop == "le":
                            prop = "max"
                        elif prop == "gt":
                            prop = "min"
                            value = value + 1
                        elif prop == "lt":
                            prop = "max"
                            value = value - 1
                        elif prop == "multiple_of":
                            prop = "step"
                        field_dict[prop] = value
                    except TypeError:
                        pass

            field_dict['value'] = getattr(self, f)
            field_dict['type'] = data.outer_type_.__name__

            # Check if 'choices' is in 'extras'
            extra_fields = ["choices", "custom_type", "group", "toggle_fields", "advanced"]
            if hasattr(data.field_info, "extra"):
                extras = getattr(data.field_info, "extra")
                for extra in extra_fields:
                    if extra in extras:
                        field_dict[extra] = extras[extra]
            keys.append(f)
            tc_fields[f] = field_dict
        tc_fields['keys'] = keys
        return tc_fields

    def as_dict(self):
        ignore_keys = []
        out_dict = {}
        for k, v in self.__dict__.items():
            try:
                if k in ignore_keys:
                    continue
                if k == "model":
                    v = v.__dict__
                val = json.dumps(v)
                out_dict[k] = val
            except TypeError:
                pass
        return out_dict
