import os.path
import numpy as np
import cv2 as cv
import matplotlib.pyplot as plt
import time
from dd2419_detector_baseline_OG.utils import run_model_singleimage


def image_preprocessing(query_img_path, train_img_path, crop):
    img1 = cv.imread(query_img_path)  # queryImage
    img2 = cv.imread(train_img_path)  # trainImage
    img2_og = img2
    img1 = cv.cvtColor(img1, cv.COLOR_BGR2GRAY)
    img2 = cv.cvtColor(img2, cv.COLOR_BGR2GRAY)

    if crop:
        height = crop["height"].item() * -1
        width = crop["width"].item()  # shitfix
        top_x = int(round(crop['x'].item()))
        top_y = int(round(crop['y'].item()))
        bottom_x = int(top_x + round(width))
        bottom_y = int(top_y - round(height))
        img2 = img2[top_y: bottom_y, top_x: bottom_x]

    else:
        top_x = 0
        top_y = 0
        bottom_x = img1.shape[0]
        bottom_y = img1.shape[1]

    object_center = ((img2.shape[0])/2, (img2.shape[1])/2)

    return img1, img2, ((bottom_x - top_x)/2, (bottom_y - top_y)/2), object_center, img2_og


def sift_feasture_detection(query_img_path, train_img_path, crop):
    img1, img2, center, object_points, img2_og = image_preprocessing(query_img_path, train_img_path, crop)
    start_time = time.time()

    # Initiate SIFT detector
    sift = cv.xfeatures2d.SIFT_create()

    # find the keypoints and descriptors with SIFT
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)
    # BFMatcher with default params
    bf = cv.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    # Apply ratio test
    good = []
    for m, n in matches:
        if m.distance < 0.9 * n.distance:
            good.append([m])
    img3 = cv.drawMatchesKnn(img1, kp1, img2, kp2, good, None, flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    plt.imshow(img3), plt.show()
    return kp1, kp2, good, img1, img2, center, object_points, img2_og

def draw(img, corners, imgpts):
    img = cv.line(img, corners, tuple(imgpts[0].ravel()), (255, 0, 0), 5)
    img = cv.line(img, corners, tuple(imgpts[1].ravel()), (0, 255, 0), 5)
    img = cv.line(img, corners, tuple(imgpts[2].ravel()), (0, 0, 255), 5)
    return img

def get_points(kp1, kp2, good, object_center):
    canonical2D_kp = np.array([kp1[item[0].queryIdx].pt for item in good])
    image_points = np.array([kp2[item[0].trainIdx].pt for item in good])
    object_points = np.zeros((image_points.shape[0], image_points.shape[1] + 1))
    object_points[:, :2] = (canonical2D_kp - object_center) / 10.0

    # trying to deal with the duplicates of signficant points

    image_rows, image_idx = np.unique(image_points, axis=0, return_index=True)
    object_rows, object_idx = np.unique(object_points, axis=0, return_index=True)
    idx = image_idx if len(image_idx) <= len(object_idx) else object_idx


    assert image_rows.shape[0] >= 4

    return object_points[idx], image_points[idx]

def get_orientation(see_image_points=False):
    my_path = os.path.abspath(os.path.dirname(__file__))
    query_img_path = os.path.join(my_path, "dd2419_traffic_sign_pdfs", "follow_right.jpg")
    train_img_path = os.path.join(my_path, "dd2419_traffic_sign_pdfs", "G6_00138.jpg")#os.path.join(my_path, "dd2419_detector_baseline_OG/performance_test/test_images",
                                  #"0000069.jpg")

    model_run = run_model_singleimage(train_img_path)[0][0]
    # model_run = None

    kp1, kp2, good, img1, img2, image_center, object_center, img2_og = sift_feasture_detection(query_img_path, train_img_path, model_run)
    result_img = img2
    plt.imshow(img2), plt.show()
    # Harded for now but will be read form camera matrix
    # I got these values from camera info
    D = np.array([0.061687, -0.049761, -0.008166, 0.004284, 0.0])
    K = np.array([231.250001, 0.0, 320.519378, 0.0, 231.065552, 240.631482, 0.0, 0.0, 1.0]).reshape(3, 3)
    P = np.array([231.25, 0.0, 322.360322, 0.0, 0.0, 231.06, 240.631, 0.0, 0.0, 0.0, 1.0, 0.0]).reshape(3, 4)
    R = np.array([1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]).reshape(3, 3)
    # TODO: replace camera values with a camera
    # D = np.array([0.0, 0.0, 0.0, 0.0, 0.0])

    axis = np.float32([[3, 0, 0], [0, 3, 0], [0, 0, 3]]).reshape(-1, 3)

    camera_matrix = K
    dist_coeffs = D
    # cv.imwrite("test.jpg", result_img)
    # object_points, image_points = get_points(kp1, kp2, good, object_center)
    image_points = np.array([[103, 65], [99, 126], [131, 97], [63, 152], [89, 28]], np.float32)
    object_points = np.zeros((image_points.shape[0], 3), np.float32)
    object_points[:, :2] = (np.array([[305, 106], [304, 282], [394, 194], [198, 366], [244, 5]]) - np.array([497/2, 480/2])) / 10.0

    if see_image_points:
        plt.imshow(img2)
        plt.scatter(image_points[:, 0], image_points[:, 1])
        plt.show()
        plt.imshow(img1)
        plt.scatter(object_points[:, 0] * 10.0 + 497/2, object_points[:, 1] * 10.0 + 480/2)
        plt.show()

    retval, rvec, tvec, _ = cv.solvePnPRansac(object_points.reshape(-1, 1, 3), image_points.reshape(-1, 1, 2), camera_matrix, dist_coeffs)
    # retval, rvec, tvec, inliers = cv.solvePnPRansac(object_points, image_points, camera_matrix, dist_coeffs)
    rotation_matrix, _ = cv.Rodrigues(rvec)

    image_points, jacobian = cv.projectPoints(axis, rvec, tvec, camera_matrix, dist_coeffs)

    result_img = draw(result_img, image_center, image_points)
    plt.imshow(result_img), plt.show()



if __name__ == "__main__":
    get_orientation(True)



