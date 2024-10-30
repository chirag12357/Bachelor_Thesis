import json
import cv2
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from PIL import Image, ImageFont, ImageDraw


def resize_pad_image(image, mask = False, new_shape=(640, 640)):
    # Resize image to fit into new_shape maintaining aspect ratio
    h, w = image.shape[:2]
    scale = min(new_shape[1] / w, new_shape[0] / h)
    nw, nh = int(w * scale), int(h * scale)

    # Resize image with the scaling factor
    resized_image = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

    if mask == True:
        new_image = np.full((new_shape[0], new_shape[1]), False, dtype=bool)
    else:
        # Create a new image with padding
        new_image = np.full((new_shape[0], new_shape[1], 3), 128, dtype=np.uint8)

    # Calculate padding
    top = (new_shape[0] - nh) // 2
    left = (new_shape[1] - nw) // 2

    # Place the resized image in the new image with padding
    new_image[top:top + nh, left:left + nw] = resized_image

    return new_image, scale, top, left

def resize_pad_mask(mask, new_shape=(640, 640)):
    # Get the original dimensions
    original_height, original_width = mask.shape
    
    # Calculate the scale to maintain aspect ratio
    scale = min(new_shape[1] / original_width, new_shape[0] / original_height)
    
    # Calculate the new width and height while maintaining aspect ratio
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    
    # Resize the mask
    resized_mask = cv2.resize(mask.astype(np.uint8), (new_width, new_height), interpolation=cv2.INTER_NEAREST)
    
    # Create a new blank mask with the target dimensions
    new_mask = np.full(new_shape, False, dtype=bool)
    
    # Calculate padding
    pad_top = (new_shape[0] - new_height) // 2
    pad_left = (new_shape[1] - new_width) // 2
    
    # Place the resized mask into the new mask with padding
    new_mask[pad_top:pad_top + new_height, pad_left:pad_left + new_width] = resized_mask.astype(bool)
    
    return new_mask, scale, pad_top, pad_left

def rle_to_binary_mask(rle):
    """Converts a COCOs run-length encoding (RLE) to binary mask.
    :param rle: Mask in RLE format
    :return: a 2D binary numpy array where '1's represent the object
    """
    binary_array = np.zeros(np.prod(rle.get('size')), dtype=bool)
    counts = rle.get('counts')

    start = 0
    for i in range(len(counts) - 1):
        start += counts[i]
        end = start + counts[i + 1]
        binary_array[start:end] = (i + 1) % 2

    binary_mask = binary_array.reshape(*rle.get('size'), order='F')

    return binary_mask

def resize_bounding_box(bbox, scale, pad_top, pad_left):
    resized_bbox = []
    for x, y in bbox:
        new_x = x * scale + pad_left
        new_y = y * scale + pad_top
        resized_bbox.append((new_x, new_y))
    return resized_bbox

path = "/home/reddy/Bachelor_Thesis/examples/part_2/coco_data"
dataset_path = "/data/reddy/Bachelor_Thesis/dataset"

existing_images = []
if os.path.exists(dataset_path + "/annotated_images"):
    existing_images = [int(i.split("_")[-1][0:-4]) for i in os.listdir(dataset_path + "/annotated_images")]


# path = "/data/reddy/coco_data"
with open(path + "/coco_annotations.json") as f:
    data = json.load(f)
    annotations = data["annotations"]
    images = data["images"]
    categories = data["categories"]
    categories = {category["id"]: category["name"] for category in categories}
    # classes = {"Honeycomb Cup for HC wall" : 0}



train_num = int(round(len(images) * 0.7))
test_num = int(round(len(images) * 0.2))
val_num = len(images) - train_num - test_num
split_list = ["train" for i in range(train_num)] + ["test" for i in range(test_num)] + ["val" for i in range(val_num)]
np.random.shuffle(split_list)

os.makedirs(dataset_path + "/train/images", exist_ok=True)
os.makedirs(dataset_path + "/test/images", exist_ok=True)
os.makedirs(dataset_path + "/val/images", exist_ok=True)
os.makedirs(dataset_path + "/train/labels", exist_ok=True)
os.makedirs(dataset_path + "/test/labels", exist_ok=True)
os.makedirs(dataset_path + "/val/labels", exist_ok=True)
os.makedirs(dataset_path + "/annotated_images", exist_ok=True)
os.makedirs(dataset_path + "/masked_images", exist_ok=True)


annotations_grouped = {}
for annotation in annotations:
    image_id = annotation["image_id"]
    if image_id not in annotations_grouped:
        annotations_grouped[image_id] = []
    annotations_grouped[image_id].append(annotation)


for image in annotations_grouped:
    if image in existing_images:
        print(f"Image {image} already exists in the dataset. Skipping...")
        continue
    img = cv2.imread(f"{path}/{images[image-2000]['file_name']}")
    image_type = split_list.pop()
    resized_image, scale, pad_top, pad_left = resize_pad_image(img)
    
    annotated_image = np.copy(resized_image)
    mask_image = Image.fromarray(cv2.cvtColor(np.copy(resized_image), cv2.COLOR_BGR2RGB))

    annotations_text = ""
    for annotation in annotations_grouped[image]:
        mask = rle_to_binary_mask(annotation["segmentation"]).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest_contour = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(largest_contour)
        (x,y),(w,h), a = rect
        
        box = cv2.boxPoints(rect)
        box = np.intp(box) #turn into ints
        resized_box = resize_bounding_box(box, scale, pad_top, pad_left)
        resized_box = np.intp(resized_box)

        Class = annotation["category_id"]
        
        annotations_text += f"{Class} {' '.join([str((coord/640)) for coord in resized_box.flatten()])}\n"
        color = (0, 255, 0) if Class == 0 else (0, 0, 255)
        annotated_image = cv2.drawContours(annotated_image, [resized_box], 0, color, 1)

        mask = resize_pad_mask(mask)[0]
        mask = mask.astype(np.uint8) * 255
        mask_image.putalpha(255)
        mask = Image.fromarray(mask, mode="L")
        overlay = Image.new('RGBA', mask_image.size)
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.bitmap((0, 0), mask, fill=(color[2], color[1], color[0], 64))
        mask_image = Image.alpha_composite(mask_image, overlay)

    with open(f"{dataset_path}/{image_type}/labels/image_{image}.txt", "w") as f:
        f.write(annotations_text)
    
    mask_image.save(f"{dataset_path}/masked_images/masked_image_{image}.png")
    cv2.imwrite(f"{dataset_path}/annotated_images/annotated_image_{image}.jpg", annotated_image)
    cv2.imwrite(f"{dataset_path}/{image_type}/images/image_{image}.jpg", resized_image)
    
    print("Done image", image)



#Converting new data to old dataset 

# import os
# import json
# import sys

# path = "/home/reddy/Bachelor_Thesis/examples/part_2/coco_data"
# dataset_path = "/data/reddy/Bachelor_Thesis/dataset2"

# existing_images = []
# if os.path.exists(dataset_path + "/annotated_images"):
#     existing_images = [int(i.split("_")[-1][0:-4]) for i in os.listdir(dataset_path + "/annotated_images")]

# # path = "/data/reddy/coco_data"
# with open(path + "/coco_annotations.json") as f:
#     data = json.load(f)

#     for image in data["images"]:
#         image["id"] = int(image["id"]+2000)
#         os.rename(path + "/" + image["file_name"], path + "/" + image["file_name"].split("/")[0] + "/" + f"{image['id']:06}.jpg")
#         image["file_name"] = image["file_name"].split("/")[0] + "/" + f"{image['id']:06}.jpg"

#     for annotation in data["annotations"]:
#         annotation["image_id"] = int(annotation["image_id"]+2000)
        

# with open(path + "/coco_annotations.json", "w") as f:
#     json.dump(data, f)

