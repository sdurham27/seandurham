from PIL import Image, ImageFilter
import os
import glob

frames_dir = os.path.join(os.path.dirname(__file__), 'frames')
output_path = os.path.join(os.path.dirname(__file__), 'saintdizzie.gif')

frame_paths = sorted(glob.glob(os.path.join(frames_dir, 'frame_*.png')))
print(f"Found {len(frame_paths)} frames")

# Use every other frame (36 frames at ~167ms = 6fps, but smoother with 72@83ms)
# Keep all 72 frames but resize to 400x400
target_size = (400, 400)

frames = []
for p in frame_paths:
    img = Image.open(p).convert('RGB')
    img = img.resize(target_size, Image.LANCZOS)
    frames.append(img)

if not frames:
    print("No frames found!")
    exit(1)

# Quantize using a good palette — use first frame as base palette
# Use adaptive palette per frame for better quality
palette_img = frames[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)

gif_frames = []
for f in frames:
    q = f.quantize(colors=128, palette=palette_img, dither=Image.Dither.NONE)
    gif_frames.append(q)

# 83ms per frame = ~12fps
gif_frames[0].save(
    output_path,
    save_all=True,
    append_images=gif_frames[1:],
    duration=83,
    loop=0,
    optimize=True
)

print(f"GIF saved to {output_path}")
size_kb = os.path.getsize(output_path) / 1024
print(f"File size: {size_kb:.1f} KB")
