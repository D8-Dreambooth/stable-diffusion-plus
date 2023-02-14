import ast


def convert_gradio_ui_to_bootstrap(file_path):
    # Step 1: Parse the Python code
    with open(file_path, "r") as f:
        code = f.read()
    parsed = ast.parse(code)

    # Step 2: Find on_ui_tabs method and extract gradio elements
    gradio_elements = []
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name == "on_ui_tabs":
            for node in ast.walk(node):
                if isinstance(node, ast.Name) and node.id.startswith("gr.") or node.id.startswith("gradio."):
                    gradio_elements.append(node)

    # Step 3: Convert gradio elements to Bootstrap HTML
    def html_constructor(tag, content="", closing_tag=True, **kwargs):
        attributes = " ".join([f'{k}="{v}"' for k, v in kwargs.items()])
        closing_tag_str = "" if not closing_tag else f"</{tag}>"
        return f"<{tag} {attributes}>{content}{closing_tag_str}"

    def button_constructor(content, **kwargs):
        return "button", content, True, kwargs

    def row_constructor(children, **kwargs):
        return "div", "".join(children), True, {"class": "row"}

    def col_constructor(children, **kwargs):
        col_size = kwargs.pop("cols", 12)
        return "div", "".join(children), True, {"class": f"col-md-{col_size}"}

    bootstrap_elements = []
    for gradio_element in gradio_elements:
        element_type = gradio_element.id.split(".")[-1]
        if element_type == "Blocks":
            bootstrap_elements.append(("div", "", True, {"class": "container", "id": gradio_element.ctx.attr}))
        elif element_type == "Row":
            children = []
            for child in gradio_element.keywords:
                if isinstance(child.value, ast.Call) and child.value.func.id in ("gr.", "gradio."):
                    child_type = child.value.func.attr
                    child_args = dict([(kw.arg, kw.value.s) for kw in child.value.keywords])
                    child_content = child_args.pop("label", "")
                    child_constructor = {
                        "Button": button_constructor,
                        "Image": html_constructor,
                        "Text": html_constructor,
                        "Slider": html_constructor,
                        "Checkbox": html_constructor
                    }[child_type]
                    children.append(child_constructor(child_content, **child_args))
            bootstrap_elements.append(row_constructor(children, **dict(gradio_element.keywords)))
        elif element_type == "Col":
            children = []
            for child in gradio_element.keywords:
                if isinstance(child.value, ast.Call) and child.value.func.id in ("gr.", "gradio."):
                    child_type = child.value.func.attr
                    child_args = dict([(kw.arg, kw.value.s) for kw in child.value.keywords])
                    child_content = child_args.pop("label", "")
                    child_constructor = {
                        "Button": button_constructor,
                        "Image": html_constructor,
                        "Text": html_constructor,
                        "Slider": html_constructor,
                        "Checkbox": html_constructor
                    }[child_type]
                    children.append(child_constructor(child_content, **child_args))
            bootstrap_elements.append(col_constructor(children, **dict(gradio_element.keywords)))

    # Step 4: Return the resulting HTML
    return "".join([html_constructor(*element) for element in bootstrap_elements])
