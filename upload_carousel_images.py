import glob
import os
from app import gcs

folder = 'mbbs_quote_images_v3'
pattern = os.path.join(folder, 'quote_*.png')
imgs = sorted(glob.glob(pattern))
urls = []
errs = []

print('Uploading images:', imgs)

for img in imgs:
    with open(img, 'rb') as f:
        url, err = gcs.upload_file(f, os.path.basename(img), 'image/png')
        urls.append(url)
        errs.append(err)
        print(f'Uploaded {img} -> {url} | Error: {err}')

print('\nAll URLs:')
for url in urls:
    print(url)

print('\nAll Errors:')
for err in errs:
    print(err) 