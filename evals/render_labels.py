"""Render synthetic pill-bottle label images from the test cabinets (Prompt A, Phase 3). No real photos.

  python -m evals.render_labels    # writes fixtures/labels/*.png and fixtures/labels/manifest.json

One label per unique bottle in the base cabinets (dx-01 variants test text normalization, not images), in three
styles: clean, blur (low-resolution and out of focus), and tilt (rotated, blurred, low contrast). The printed fields are the ground truth.
"""
import json
import textwrap
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fixtures" / "labels"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def _phone_blur(im):
    # low-resolution, out-of-focus photo: downscale, upscale, blur
    small = im.resize((im.width * 2 // 5, im.height * 2 // 5), Image.BILINEAR)
    return small.resize(im.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.4))


def _tilted(im):
    # bottle at an angle under dim light: rotate, blur, low contrast
    im = im.rotate(9, expand=True, fillcolor="white", resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    return ImageEnhance.Contrast(im).enhance(0.45)


STYLES = {"clean": lambda im: im, "blur": _phone_blur, "tilt": _tilted}
SKIP = {("dx-07", "cab-4")}  # "unreadable" is itself a vision-step output; there is no printed label to render


def draw(name, strength, directions):
    small, big = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 30)
    im = Image.new("RGB", (760, 280), "white")
    d = ImageDraw.Draw(im)
    d.text((20, 14), "BRIGHTON PHARMACY   617-555-0123", font=small, fill="black")
    d.text((20, 44), "Rx 4410235   Qty 30   Refills 1", font=small, fill="black")
    d.text((20, 74), "Patient: Rosa Delgado", font=small, fill="black")
    d.line((20, 108, 740, 108), fill="black", width=2)
    d.text((20, 118), name, font=big, fill="black")
    d.text((20, 160), f"Strength: {strength}", font=small, fill="black")
    for i, line in enumerate(textwrap.wrap(directions, 58)):
        d.text((20, 194 + 30 * i), line, font=small, fill="black")
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    labels, cabinets = {}, {}
    for case in yaml.safe_load((ROOT / "evals" / "cases" / "cabinet_diff.yaml").read_text()):
        for item in case["cabinet"]:
            if (case["id"], item["id"]) in SKIP:
                continue
            key = (item["name"], item["strength"], item["directions"])
            if key not in labels:
                labels[key] = f"label-{len(labels) + 1:02d}"
            cabinets.setdefault(case["id"], {})[item["id"]] = labels[key]
    manifest = {"labels": [], "cabinets": cabinets}
    for (name, strength, directions), label_id in labels.items():
        base = draw(name, strength, directions)
        for style, fx in STYLES.items():
            path = OUT / f"{label_id}_{style}.png"
            fx(base).save(path)
            manifest["labels"].append({"label": label_id, "style": style, "path": str(path.relative_to(ROOT)),
                                       "truth": {"name": name, "strength": strength, "directions": directions}})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(labels)} unique labels x {len(STYLES)} styles = {len(manifest['labels'])} images -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
