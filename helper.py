
import json
import math

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import cv2


WHITE = (255, 255, 255)
YELLOW = (66, 244, 238)
GREEN = (80, 220, 60)
LIGHT_CYAN = (255, 255, 224)
DARK_BLUE = (139, 0, 0)
GRAY = (128, 128, 128)
START_LINE = 0

def detect_objects(filename,MAXIMO_VISUAL_INSPECTION_API_URL):
    with open(filename, 'rb') as f:
        # WARNING! verify=False is here to allow an untrusted cert!
        r = requests.post(MAXIMO_VISUAL_INSPECTION_API_URL,
                   files={'files': (filename, f)},
                   verify=False)

    return r.status_code, json.loads(r.text)


def label_object(color, textcolor, fontface, image, car, textsize, thickness, xmax, xmid, xmin, ymax, ymid, ymin):
    cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, thickness)
    pos = (xmid - textsize[0] // 2, ymid + textsize[1] // 2)
    cv2.putText(image, car, pos, fontface, 1, textcolor, thickness, cv2.LINE_AA)


def update_trackers(image, counters,trackers):
    height, width, channels = image.shape
    ROI_YMAX = height

    left_lane = counters['left_lane']
    right_lane = counters['right_lane']
    boxes = []
    color = (80, 220, 60)
    fontface = cv2.FONT_HERSHEY_SIMPLEX
    fontscale = 1
    thickness = 1

    for n, pair in enumerate(trackers):
        tracker, car = pair
        textsize, _baseline = cv2.getTextSize(
            car, fontface, fontscale, thickness)
        success, bbox = tracker.update(image)

        if not success:
            counters['lost_trackers'] += 1
            del trackers[n]
            continue

        boxes.append(bbox)  # Return updated box list

        xmin = int(bbox[0])
        ymin = int(bbox[1])
        xmax = int(bbox[0] + bbox[2])
        ymax = int(bbox[1] + bbox[3])
        xmid = int(round((xmin + xmax) / 2))
        ymid = int(round((ymin + ymax) / 2))

        if ymid >= ROI_YMAX:
            label_object(WHITE, WHITE, fontface, image, car, textsize, 1, xmax, xmid, xmin, ymax, ymid, ymin)
            # Count left-lane, right-lane as cars ymid crosses finish line
            if xmid < 630:
                left_lane += 1
            else:
                right_lane += 1
            # Stop tracking cars when they hit finish line
            del trackers[n]
        else:
            # Rectangle and number on the cars we are tracking
            label_object(color, YELLOW, fontface, image, car, textsize, 4, xmax, xmid, xmin, ymax, ymid, ymin)

    # Add finish line overlay/line
    overlay = image.copy()

    # modified---
    height, width, channels = overlay.shape
    FRAME_WIDTH = width
    FRAME_HEIGHT = height
    ROI_YMAX = height

    # Shade region of interest (ROI). We're really just using the top line.

    cv2.rectangle(overlay,
                  (0, ROI_YMAX),
                  (FRAME_WIDTH, FRAME_HEIGHT), DARK_BLUE, cv2.FILLED)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)

    # Draw start line, if > 0
    if START_LINE > 0:
        cv2.line(image, (0, START_LINE), (FRAME_WIDTH, START_LINE), GRAY, 4, cv2.LINE_AA)
    # Draw finish line with lane hash marks
    # modified---
    height, width, channels = image.shape
    ROI_YMAX = height
    FRAME_WIDTH = width
    FRAME_FPS = 1
    # ---

    cv2.line(image, (0, ROI_YMAX), (FRAME_WIDTH, ROI_YMAX), LIGHT_CYAN, 4, cv2.LINE_AA)
    cv2.line(image, (350, ROI_YMAX - 20), (350, ROI_YMAX + 20), LIGHT_CYAN, 4, cv2.LINE_AA)
    cv2.line(image, (630, ROI_YMAX - 20), (630, ROI_YMAX + 20), LIGHT_CYAN, 4, cv2.LINE_AA)
    cv2.line(image, (950, ROI_YMAX - 20), (950, ROI_YMAX + 20), LIGHT_CYAN, 4, cv2.LINE_AA)

    # Add lane counter
    cv2.putText(image, "Lane counter:", (30, ROI_YMAX + 80), fontface, 1.5, LIGHT_CYAN, 4, cv2.LINE_AA)
    cv2.putText(image, str(left_lane), (480, ROI_YMAX + 80), fontface, 1.5, LIGHT_CYAN, 4, cv2.LINE_AA)
    cv2.putText(image, str(right_lane), (800, ROI_YMAX + 80), fontface, 1.5, LIGHT_CYAN, 4, cv2.LINE_AA)
    seconds = counters['frames'] / FRAME_FPS
    cv2.putText(image, "Cars/second:", (35, ROI_YMAX + 110), fontface, 0.5, LIGHT_CYAN, 1, cv2.LINE_AA)
    cv2.putText(image, '{0:.2f}'.format(left_lane / seconds), (480, ROI_YMAX + 110), fontface, 0.5, LIGHT_CYAN, 1,
                cv2.LINE_AA)
    cv2.putText(image, '{0:.2f}'.format(right_lane / seconds), (800, ROI_YMAX + 110), fontface, 0.5, LIGHT_CYAN, 1,
                cv2.LINE_AA)

    counters['left_lane'] = left_lane
    counters['right_lane'] = right_lane
    return boxes, counters,trackers



def not_tracked(objects, boxes):
    if not objects:
        return []  # No new classified objects to search for
    if not boxes:
        return objects  # No existing boxes, return all objects

    new_objects = []
    for obj in objects:
        ymin = obj.get("ymin", "")
        ymax = obj.get("ymax", "")
        ymid = int(round((ymin+ymax)/2))
        xmin = obj.get("xmin", "")
        xmax = obj.get("xmax", "")
        xmid = int(round((xmin+xmax)/2))
        box_range = ((xmax - xmin) + (ymax - ymin)) / 2
        for bbox in boxes:
            bxmin = int(bbox[0])
            bymin = int(bbox[1])
            bxmax = int(bbox[0] + bbox[2])
            bymax = int(bbox[1] + bbox[3])
            bxmid = int((bxmin + bxmax) / 2)
            bymid = int((bymin + bymax) / 2)
            if math.sqrt((xmid - bxmid)**2 + (ymid - bymid)**2) < box_range:
                # found existing, so break (do not add to new_objects)
                break
        else:
            new_objects.append(obj)

    return new_objects


def in_range(obj):
    ymin = obj['ymin']
    ymax = obj['ymax']
    #     if ymin < START_LINE or ymax > ROI_YMAX:
    #         # Don't add new trackers before start or after finish.
    #         # Start line can help avoid overlaps and tracker loss.
    #         # Finish line protection avoids counting the car twice.
    #         return False
    return True


def add_new_object(obj, image, cars,trackers):
    car = str(cars)
    xmin = obj['xmin']
    xmax = obj['xmax']
    ymin = obj['ymin']
    ymax = obj['ymax']
    xmid = int(round((xmin + xmax) / 2))
    ymid = int(round((ymin + ymax) / 2))
    fontface = cv2.FONT_HERSHEY_SIMPLEX
    fontscale = 1
    thickness = 1
    textsize, _baseline = cv2.getTextSize(
        car, fontface, fontscale, thickness)

    # init tracker
    tracker = cv2.TrackerKCF_create()  # Note: Try comparing KCF with MIL
    success = tracker.init(image, (xmin, ymin, xmax - xmin, ymax - ymin))
    if success:
        trackers.append((tracker, car))

    label_object(GREEN, YELLOW, fontface, image, car, textsize, 4, xmax, xmid, xmin, ymax, ymid, ymin)

