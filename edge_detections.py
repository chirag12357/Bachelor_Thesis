import cv2
import numpy as np
import os

def canny_edge(image, path="", annotation=False):
    # Convert image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Canny edge detection
    edges = cv2.Canny(gray, threshold1=75, threshold2=75)

    edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    if path:
        cv2.imwrite(path, edges_color)
    
    if annotation:
        annotated_image = cv2.drawContours(edges_color, [annotation[1]], 0, (255, 255, 255), 1)
        #split tail and head
        path = f"{annotation[0]}/annotated_images/canny/" + os.path.split(path)[1]
        
        cv2.imwrite(f"{path}", annotated_image)
    return edges_color

def active_canny(image, path="", annotation=False):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Compute the median of the pixel intensities
    median_intensity = np.median(gray)

    # Set lower and upper thresholds for Canny edge detection based on median intensity
    # These constants can be adjusted for more or less sensitivity
    sigma = 0.2
    lower_threshold = int(max(0, (1.0 - sigma) * median_intensity))
    upper_threshold = int(min(255, (1.0 + sigma) * median_intensity))

    # Apply Canny edge detection with adaptive thresholds
    edges = cv2.Canny(gray, lower_threshold, upper_threshold)

    # Convert edges to BGR so it can be stacked with the original image
    edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # # Stack the original image and edge-detected image side by side
    # combined_image = np.hstack((image, edges_color))

    if path:
        cv2.imwrite(path, edges_color)

    if annotation:
        annotated_image = cv2.drawContours(edges_color, [annotation[1]], 0, (255, 255, 255), 1)
        #split tail and head
        path = f"{annotation[0]}/annotated_images/active_canny/" + os.path.split(path)[1]
        
        cv2.imwrite(f"{path}", annotated_image)
    return edges_color
 
def hed_edge(image, path="", annotation=False):
    # Prepare the image for HED

    (h, w) = image.shape[:2]
    blob = cv2.dnn.blobFromImage(image, scalefactor=1.0, size=(640, 640), mean=(104.00698793, 116.66876762, 122.67891434), swapRB=False, crop=True)

    # Pass the image blob through the HED model
    net.setInput(blob)

    # Specify the layer names to capture intermediate outputs
    layer_names = ['sigmoid-dsn1', 'sigmoid-dsn2', 'sigmoid-dsn3', 'sigmoid-dsn4', 'sigmoid-dsn5', 'sigmoid-fuse']
    outputs = net.forward(layer_names)
    
    # Process and resize each output to match the original image dimensions
    output_images = [(255 * cv2.resize(out[0, 0], (w, h))).astype("uint8") for out in outputs]
    
    # Convert each edge map to BGR so it can be stacked with the original image
    output_images_bgr = [cv2.cvtColor(out_img, cv2.COLOR_GRAY2BGR) for out_img in output_images]

    # # Stack the original image and each of the intermediate outputs side by side
    # combined_image = np.hstack([image] + output_images_bgr)

    if path:
        for i, output_image in enumerate(output_images_bgr):
            path = path.replace("PlAcEhOlDeR", str(i+1))
            cv2.imwrite(path, output_image)
            

            if annotation:
                temp_path = path
                annotated_image = cv2.drawContours(output_image, [annotation[1]], 0, (255, 255, 255), 1)
                #split tail and head
                temp_path = f"{annotation[0]}/annotated_images/HED/{i+1}/" + os.path.split(path)[1]
                cv2.imwrite(f"{temp_path}", annotated_image)
            
            path = path.replace(f"/{str(i+1)}/", "/PlAcEhOlDeR/")
            
    return output_images_bgr

prototxt_path = 'Bachelor_Thesis/HED_Files/deploy.prototxt'
caffemodel_path = 'Bachelor_Thesis/HED_Files/hed_pretrained_bsds.caffemodel'
net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)
print("HED model loaded successfully")
