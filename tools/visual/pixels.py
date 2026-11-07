"""Compare static chart PNGs at native resolution. Used by tests and report generation."""

from PIL import Image, ImageChops, ImageFilter


def max_channel(image):
    red, green, blue, alpha = image.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), ImageChops.lighter(blue, alpha))


def compare(expected, actual):
    if expected.size != actual.size:
        raise ValueError(f"PNG dimensions differ: {expected.size} vs {actual.size}")
    expected, actual = expected.convert("RGBA"), actual.convert("RGBA")
    error = max_channel(ImageChops.difference(expected, actual))
    hist = error.histogram()
    # Flat-color regions must match exactly. Only the one-pixel neighborhood of
    # an actual upstream edge may differ through rasterization or font hinting.
    flat_error = error.copy()
    for channel in expected.split():
        spread = ImageChops.subtract(channel.filter(ImageFilter.MaxFilter(3)),
                                     channel.filter(ImageFilter.MinFilter(3)))
        flat_error.paste(0, mask=spread.point(lambda x: 255 if x else 0))
    pixels = expected.width * expected.height
    metrics = {
        "different_pixels": sum(hist[1:]),
        "flat_region_errors": sum(flat_error.histogram()[1:]),
        "peak_channel_error": error.getextrema()[1],
        "fraction_over_32": sum(hist[33:]) / pixels,
        "mean_max_channel_error": sum(i * n for i, n in enumerate(hist)) / pixels,
    }
    return metrics, error


def passes(metrics):
    return (metrics["flat_region_errors"] == 0 and metrics["peak_channel_error"] <= 120
            and metrics["fraction_over_32"] <= 0.002 and metrics["mean_max_channel_error"] <= 0.4)
