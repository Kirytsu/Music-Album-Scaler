from mutagen.flac import FLAC
import os, sys

def inspect(p):
    if not os.path.exists(p):
        print('MISSING', p)
        return
    f = FLAC(p)
    print('\nFILE:', p)
    print('TAG KEYS:', list(f.tags.keys()) if f.tags else 'No tags')
    print('PICTURES:', len(f.pictures))
    for i, pic in enumerate(f.pictures):
        print('PIC[{}]'.format(i))
        print('  mime:', pic.mime)
        print('  type:', getattr(pic, 'type', None))
        print('  description:', repr(getattr(pic, 'description', None)))
        print('  width/height/depth/colors:', getattr(pic, 'width', None), getattr(pic, 'height', None), getattr(pic, 'depth', None), getattr(pic, 'colors', None))
        print('  data length:', len(pic.data))
        try:
            from PIL import Image
            import io
            im = Image.open(io.BytesIO(pic.data))
            print('  image format:', im.format, 'size:', im.size, 'mode:', im.mode)
        except Exception as e:
            print('  image open error:', e)

if __name__ == '__main__':
    # Array of files path to inspect
    files = ['example.flac', 'example2.flac', '']
    for p in files:
        inspect(p)
