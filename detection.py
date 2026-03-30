import cv2
import numpy as np
import json
import os
from math import exp
from hailo_platform import HEF, VDevice, ConfigureParams, HailoStreamInterface, InferVStreams, InputVStreamParams, OutputVStreamParams, FormatType

class CustomObjectDetector:
    def __init__(self, hef_path, labels_path, conf_threshold=0.3):
        """
        Initializes the Hailo device and loads the model.
        """
        self.conf_threshold = conf_threshold
        self.labels_path = labels_path  # store for later use in postprocess

        # Load configuration and labels from JSON
        with open(labels_path, 'r') as f:
            config = json.load(f)
            labels_list = config["labels"]                # list of class names
            offset = config.get("label_offset", 0)        # optional offset
            # Build dictionary mapping actual class IDs (with offset) to names
            self.labels = {str(i + offset): name for i, name in enumerate(labels_list)}
            # Also keep full config for anchors etc.
            self.config = config

        # Initialize Hailo device and model
        self.device = VDevice()
        self.hef = HEF(hef_path)

        configure_params = ConfigureParams.create_from_hef(hef=self.hef, interface=HailoStreamInterface.PCIe)
        self.network_groups = self.device.configure(self.hef, configure_params)
        self.network_group = self.network_groups[0]

        self.input_vstream_info = self.hef.get_input_vstream_infos()[0]
        self.output_vstream_infos = self.hef.get_output_vstream_infos()
        self.input_height, self.input_width, self.input_channels = self.input_vstream_info.shape

        print(f"Model loaded: Input shape: {self.input_width}x{self.input_height}")
        print(f"Labels loaded with offset {offset}: {self.labels}")

    def preprocess(self, image_path):
        """
        Preprocesses an image for inference (resize and convert to RGB).
        Returns preprocessed array (uint8) and original BGR image.
        """
        # Read image using OpenCV
        image_bgr = cv2.imread(image_path)
        if image_bgr is None:
            raise ValueError(f"Could not read image from {image_path}")
        
        # Convert BGR to RGB and resize to model input size
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized_image = cv2.resize(image_rgb, (self.input_width, self.input_height))
        
        # Model expects UINT8 input (from parse-hef)
        input_data = np.expand_dims(resized_image, axis=0).astype(np.uint8)
        return input_data, image_bgr

    def run_inference(self, preprocessed_frame):
        """
        Runs inference on the preprocessed frame.
        Returns dict of output tensors.
        """
        input_data = {self.input_vstream_info.name: preprocessed_frame}
        
        # Create input/output stream parameters (UINT8 input, FLOAT32 output as shown in debug)
        input_vstreams_params = InputVStreamParams.make(self.network_group, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make(self.network_group, format_type=FormatType.FLOAT32)
        
        # Run inference
        with InferVStreams(self.network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
            with self.network_group.activate():
                infer_results = infer_pipeline.infer(input_data)
        
        return infer_results

    def postprocess(self, raw_outputs, original_image):
        """
        Decode YOLO outputs from multiple tensors.
        raw_outputs: dict from tensor name to numpy array
        original_image: BGR image (for drawing and size reference)
        Returns list of detections.
        """
        orig_h, orig_w = original_image.shape[:2]
        input_w, input_h = self.input_width, self.input_height  # 640x640

        # Get parameters from config
        anchors = self.config["anchors"]  # list of three scales
        num_classes = len(self.config["labels"])
        offset = self.config.get("label_offset", 1)
        conf_thresh = self.conf_threshold

        # Map tensor names to scales (based on your parse-hef output)
        # scale 80x80: conv41 (64) + conv42 (2)
        # scale 40x40: conv52 (64) + conv53 (2)
        # scale 20x20: conv62 (64) + conv63 (2)
        scales = [
            {"bbox": "beach_robot/conv41", "cls": "beach_robot/conv42", "grid": 80, "anchor_idx": 2},
            {"bbox": "beach_robot/conv52", "cls": "beach_robot/conv53", "grid": 40, "anchor_idx": 1},
            {"bbox": "beach_robot/conv62", "cls": "beach_robot/conv63", "grid": 20, "anchor_idx": 0},
        ]

        detections = []

        for scale_info in scales:
            bbox_tensor = raw_outputs[scale_info["bbox"]][0]  # (grid, grid, 64)
            cls_tensor  = raw_outputs[scale_info["cls"]][0]   # (grid, grid, 2)
            grid_size = scale_info["grid"]
            anchor_set = anchors[scale_info["anchor_idx"]]    # list of 6 numbers (3 pairs)

            # Assume first 15 channels are (3 anchors * (4+1)) = tx,ty,tw,th,obj
            bbox_raw = bbox_tensor[..., :15].reshape(grid_size, grid_size, 3, 5)
            # bbox_raw[..., 0:4] = raw tx, ty, tw, th
            # bbox_raw[..., 4]   = raw objectness logit

            cls_logits = cls_tensor  # (grid, grid, 2) raw class logits

            # Helper sigmoid
            def sigmoid(x):
                return 1 / (1 + np.exp(-x))

            for y in range(grid_size):
                for x in range(grid_size):
                    for a in range(3):
                        tx, ty, tw, th, obj_logit = bbox_raw[y, x, a]

                        # Apply sigmoid to tx, ty, obj_logit (YOLO convention)
                        tx = sigmoid(tx)
                        ty = sigmoid(ty)
                        obj_prob = sigmoid(obj_logit)

                        if obj_prob < conf_thresh:
                            continue

                        # Class probabilities from cls_tensor (sigmoid)
                        class_probs = sigmoid(cls_logits[y, x])   # shape (2,)
                        class_id = np.argmax(class_probs)
                        class_conf = class_probs[class_id]

                        total_conf = obj_prob * class_conf
                        if total_conf < conf_thresh:
                            continue

                        # Decode box to absolute coordinates (YOLO formula)
                        # bx = (tx + x) / grid_size
                        # by = (ty + y) / grid_size
                        # bw = anchor_w * exp(tw) / input_w
                        # bh = anchor_h * exp(th) / input_h
                        anchor_w = anchor_set[a*2]
                        anchor_h = anchor_set[a*2 + 1]

                        bx = (tx + x) / grid_size
                        by = (ty + y) / grid_size
                        bw = anchor_w * exp(tw) / input_w
                        bh = anchor_h * exp(th) / input_h

                        # Convert to pixel coordinates in original image
                        xmin = int((bx - bw/2) * orig_w)
                        ymin = int((by - bh/2) * orig_h)
                        xmax = int((bx + bw/2) * orig_w)
                        ymax = int((by + bh/2) * orig_h)

                        # Clamp to image boundaries
                        xmin = max(0, xmin)
                        ymin = max(0, ymin)
                        xmax = min(orig_w, xmax)
                        ymax = min(orig_h, ymax)

                        if xmax > xmin and ymax > ymin:
                            detections.append({
                                "bbox": [xmin, ymin, xmax, ymax],
                                "score": float(total_conf),
                                "category_id": int(class_id) + offset,
                                "label": self.config["labels"][class_id]  # offset handled by index
                            })

        # Apply NMS
        detections = self.non_max_suppression(detections, iou_threshold=self.config.get("iou_threshold", 0.45))
        return detections

    def non_max_suppression(self, detections, iou_threshold=0.45):
        """Simple NMS based on intersection over union."""
        if not detections:
            return []
        # Sort by score descending
        detections = sorted(detections, key=lambda d: d["score"], reverse=True)
        keep = []
        while detections:
            best = detections.pop(0)
            keep.append(best)
            # Remove any remaining with high IoU
            to_remove = []
            for i, det in enumerate(detections):
                if self.iou(best["bbox"], det["bbox"]) > iou_threshold:
                    to_remove.append(i)
            for i in reversed(to_remove):
                detections.pop(i)
        return keep

    def iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0


# ----------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # File paths (all siblings of the script)
    HEF_PATH = os.path.join(script_dir, "beach_robot.hef")          # your model file
    LABELS_PATH = os.path.join(script_dir, "beach_robot_labels.json")
    IMAGE_PATH = os.path.join(script_dir, "jellyfish.png")

    # Verify files exist
    for path in [HEF_PATH, LABELS_PATH, IMAGE_PATH]:
        if not os.path.exists(path):
            print(f"Error: File not found: {path}")
            exit(1)

    # 1. Initialize detector (use a low threshold for testing)
    detector = CustomObjectDetector(HEF_PATH, LABELS_PATH, conf_threshold=0.1)

    # 2. Preprocess image
    preprocessed_img, original_img = detector.preprocess(IMAGE_PATH)

    # 3. Run inference
    print("Running inference...")
    raw_results = detector.run_inference(preprocessed_img)

    # Optional: print output tensor info for debugging
    print("Number of output tensors:", len(raw_results))
    for name, tensor in raw_results.items():
        print(f"{name}: shape {tensor.shape}, dtype {tensor.dtype}")
        print(f"  min={tensor.min():.2f}, max={tensor.max():.2f}, mean={tensor.mean():.2f}")
        # print first few values
        flat = tensor.flatten()
        print(f"  first 20 values: {flat[:20]}")

    # 4. Postprocess
    final_detections = detector.postprocess(raw_results, original_img)

    # 5. Print detections
    print(f"Found {len(final_detections)} objects:")
    for det in final_detections:
        print(f"  - {det['label']}: {det['score']:.2f} at {det['bbox']}")

    # 6. Draw boxes on the image
    for det in final_detections:
        xmin, ymin, xmax, ymax = det['bbox']
        cv2.rectangle(original_img, (xmin, ymin), (xmax, ymax), (255, 0, 0), 5)
        cv2.putText(original_img, f"{det['label']} {det['score']:.2f}", (xmin, ymin-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 0, 0), 8)

    # Save output image
    output_path = os.path.join(script_dir, "output.jpg")
    cv2.imwrite(output_path, original_img)
    print(f"Output saved to {output_path}")
