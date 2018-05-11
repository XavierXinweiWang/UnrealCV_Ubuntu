from __future__ import division, absolute_import, print_function
import os, sys, time, re, json
import numpy as np
import matplotlib.pyplot as plt
from unrealcv import client
import PIL.Image

imread = plt.imread


# TODO: replace this with a better implementation
class Color(object):
    ''' A utility class to parse color value '''
    regexp = re.compile('\(R=(.*),G=(.*),B=(.*),A=(.*)\)')

    def __init__(self, color_str):
        self.color_str = color_str
        match = self.regexp.match(color_str)
        (self.R, self.G, self.B, self.A) = [int(match.group(i)) for i in range(1,5)]

    def __repr__(self):
        return self.color_str


def imread8(im_file):
    ''' Read image as a 8-bit numpy array '''
    im = np.asarray(PIL.Image.open(im_file))
    return im


def read_png(res):
    img = PIL.Image.open(res)
    return np.asarray(img)


# TODO: Fix this function
def read_npy(res):
    return np.load(res)


def match_color(object_mask, target_color, tolerance=3):
    match_region = np.ones(object_mask.shape[0:2], dtype=bool)
    for c in range(3):  # r,g,b
        min_val = target_color[c] - tolerance
        max_val = target_color[c] + tolerance
        channel_region = (object_mask[:,:,c] >= min_val) & (object_mask[:,:,c] <= max_val)
        match_region &= channel_region

    if match_region.sum() != 0:
        return match_region
    else:
        return None


def main():
    client.connect()  # Connect to the game
    if not client.isconnected():  # Check if the connection is successfully established
        print('UnrealCV server is not running.')
        sys.exit(-1)
    else:
        res = client.request('vget /unrealcv/status')
        # The image resolution and port is configured in the config file.
        print(res)

        traj_file = '../../docs/tutorials_source/camera_traj.json'
        camera_trajectory = json.load(open(traj_file))

        idx = 1
        loc, rot = camera_trajectory[idx]
        # Set position of the first camera
        client.request('vset /camera/0/location {x} {y} {z}'.format(**loc))
        client.request('vset /camera/0/rotation {pitch} {yaw} {roll}'.format(**rot))

        # Get image
        res = client.request('vget /camera/0/lit lit.png')
        print('The image is saved to %s' % res)
        im = read_png(res)

        # Generate Ground Truth
        res = client.request('vget /camera/0/object_mask object_mask.png')
        print('The image is saved to %s' % res)
        object_mask = read_png(res)
        res = client.request('vget /camera/0/normal normal.png')
        print('The image is saved to %s' % res)
        normal = read_png(res)

        # Generate Depth
        res = client.request('vget /camera/0/depth depth.png')
        print('The image is saved to %s' % res)

        # Get objects from the scene
        scene_objects = client.request('vget /objects').split(' ')
        print('Number of objects in this scene: ', len(scene_objects))
        print('They are: ', scene_objects)

        # Map from object id to the labeling color
        id2color = {}
        for obj_id in scene_objects:
            color = Color(client.request('vget /object/%s/color' % obj_id))
            id2color[obj_id] = color
            # print('%s : %s' % (obj_id, str(color)))

        id2mask = {}
        for obj_id in scene_objects:
            color = id2color[obj_id]
            mask = match_color(object_mask, [color.R, color.G, color.B], tolerance=3)
            if mask is not None:
                id2mask[obj_id] = mask

        obj_file = '../../docs/tutorials_source/object_category.json'
        with open(obj_file) as f:
            id2category = json.load(f)
        categories = set(id2category.values())
        # Show statistics of this frame
        image_objects = id2mask.keys()
        print('Number of objects in this image:', len(image_objects))
        print('%20s : %s' % ('Category name', 'Object name'))
        for category in categories:
            objects = [v for v in image_objects if id2category.get(v) == category]
            if len(objects) > 6:  # Trim the list if too long
                objects[6:] = ['...']
            if len(objects) != 0:
                print('%20s : %s' % (category, objects))

        # Plot objs
        vase_instance = [v for v in image_objects if id2category.get(v) == 'Vase']
        mask = sum(id2mask[v] for v in vase_instance)
        plt.figure()
        plt.imshow(mask, cmap="gray")
        plt.show()

        client.disconnect()

main()
