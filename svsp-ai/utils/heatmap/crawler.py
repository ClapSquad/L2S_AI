from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import numpy as np
import matplotlib.pyplot as plt
import argparse

CONST_YOUTUBE_HEATMAP_X_RANGE = 1000.0
CONST_YOUTUBE_HEATMAP_Y_BASE = 100.0
PARAM_GAUSSIAN_SMOOTHING_SIGMA = 1
PARAM_EXTREMUM_ONE_SIDE_WINDOW_SIZE_IN_SECONDS = 1
PARAM_EXTREMUM_PICK_WINDOW_SIZE_IN_SECONDS = 30


def get_heatmap_path_and_duration(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    try:
        wait = WebDriverWait(driver, 15)

        # Heatmap
        path_elem = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "path.ytp-modern-heat-map"))
        )
        svg_html = path_elem.get_attribute("outerHTML")

        # Video duration
        duration_elem = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.ytp-time-duration"))
        )
        duration_text = duration_elem.text
        return svg_html, duration_text

    except Exception as e:
        print("SVG not found:", e)
        return None
    finally:
        driver.quit()


def get_d_from_path(path_html: str) -> str | None:
    return BeautifulSoup(path_html, "html.parser").find("path")["d"]


def time_to_seconds(time_str: str) -> float:
    parts = [int(p) for p in time_str.split(":")]
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0, *parts
    else:
        return 0
    return h * 3600 + m * 60 + s


def process_heatmap_to_highlight_point(d_attr: str, duration_in_seconds):
    def sample_points_from_path(d_attr):
        sampled_points = re.findall(r"([0-9.]+),([\-0-9.]+)", d_attr)
        return np.array([(float(x), CONST_YOUTUBE_HEATMAP_Y_BASE - float(y)) for x, y in sampled_points])

    def normalize(points):
        y = points[:, 1]
        x = points[:, 0]
        min_y, max_y = y.min(), y.max()
        y_norm = (y - min_y) / (max_y - min_y)
        return np.column_stack((x, y_norm))

    def gaussian_smooth(points, sigma):
        """NumPy만으로 Gaussian smoothing (y축만 부드럽게)"""
        y = points[:, 1]
        x = points[:, 0]

        # sigma에 따라 커널 크기 결정 (보통 6*sigma 정도)
        size = int(6 * sigma + 1)
        kernel_x = np.linspace(-3 * sigma, 3 * sigma, size)
        kernel = np.exp(-0.5 * (kernel_x / sigma) ** 2)
        kernel /= np.sum(kernel)

        y_smooth = np.convolve(y, kernel, mode="same")

        return np.column_stack((x, y_smooth))

    def find_local_extremum(points, window, mode="min"):
        """
        범위(window) 기반 local minima 또는 maxima 찾기
        - window: 양쪽 비교 범위 크기 (예: 3이면 앞뒤 3개씩)
        - mode: "min" 또는 "max"
        """
        y = points[:, 1]
        n = len(y)
        minima_mask = np.zeros(n, dtype=bool)

        for i in range(window, n - window):
            local_range = y[i - window:i + window + 1]
            if mode == "min" and y[i] == np.min(local_range):
                minima_mask[i] = True
            elif mode == "max" and y[i] == np.max(local_range):
                minima_mask[i] = True

        return points[minima_mask]

    def compute_relative_positions(minima_points, points):
        min_x, max_x = points[:, 0].min(), points[:, 0].max()
        ratios = (minima_points[:, 0] - min_x) / (max_x - min_x)
        return ratios

    def pick_max_in_window(minima_points, window):
        selected = []
        min_x, max_x = minima_points[:, 0].min(), minima_points[:, 0].max()
        current_start = min_x

        while current_start < max_x:
            current_end = current_start + window
            segment = minima_points[
                (minima_points[:, 0] >= current_start) & (minima_points[:, 0] < current_end)
                ]
            if len(segment) > 0:
                best = segment[np.argmax(segment[:, 1])]
                selected.append(best)

            current_start = current_end

        return np.array(selected)

    points = sample_points_from_path(d_attr)
    points = normalize(points)
    points = gaussian_smooth(points, sigma=PARAM_GAUSSIAN_SMOOTHING_SIGMA)
    maxima_points = find_local_extremum(points,
                                        int(CONST_YOUTUBE_HEATMAP_X_RANGE / duration_in_seconds * PARAM_EXTREMUM_ONE_SIDE_WINDOW_SIZE_IN_SECONDS),
                                        "max")
    maxima_points = pick_max_in_window(maxima_points,
                                       CONST_YOUTUBE_HEATMAP_X_RANGE / duration_in_seconds * PARAM_EXTREMUM_PICK_WINDOW_SIZE_IN_SECONDS)
    timestamp_ratio = compute_relative_positions(maxima_points, points)
    return points, maxima_points, timestamp_ratio


def visualize(points, maxima_points, timestamp_ratio, duration_in_seconds):
    print("Heatmap local peaks timestamps")
    for (x, y), r in zip(maxima_points, timestamp_ratio):
        print(f"x={x:.1f}, y={y:.1f} → 전체 x의 {100 * r:.2f}%, timestamp={r * duration_in_seconds:.2f}")

    plt.figure(figsize=(10, 5))
    plt.plot(points[:, 0], points[:, 1], label="Heatmap Curve")
    plt.scatter(maxima_points[:, 0], maxima_points[:, 1], color='red', s=50, label="Peaks (local maxima)")

    plt.title("YouTube Heatmap Path Visualization")
    plt.xlabel("X (Progress along video)")
    plt.ylabel("Y (View density)")
    plt.legend()
    plt.grid(True)
    plt.show()


def get_most_watched_timestamp(video_id: str, show_on_graph=False):
    path_html, video_duration = get_heatmap_path_and_duration(video_id)
    if path_html:
        print("✅ Heatmap found")
    else:
        print("❌ Heatmap not found")
        return
    d = get_d_from_path(path_html)
    duration_in_seconds = time_to_seconds(video_duration)

    # For test without web crawling logic

    # aOwmt39L2IQ
    # d = "M 0.0,100.0 C 1.0,82.1 2.0,21.3 5.0,10.3 C 8.0,-0.8 11.0,34.5 15.0,44.7 C 19.0,54.9 21.0,56.0 25.0,61.3 C 29.0,66.7 31.0,67.4 35.0,71.2 C 39.0,75.0 41.0,82.0 45.0,80.4 C 49.0,78.8 51.0,72.1 55.0,63.1 C 59.0,54.0 61.0,39.1 65.0,35.1 C 69.0,31.1 71.0,39.4 75.0,43.1 C 79.0,46.8 81.0,51.0 85.0,53.5 C 89.0,56.1 91.0,52.1 95.0,55.9 C 99.0,59.7 101.0,69.4 105.0,72.7 C 109.0,76.0 111.0,75.2 115.0,72.4 C 119.0,69.6 121.0,61.3 125.0,58.8 C 129.0,56.3 131.0,57.0 135.0,60.0 C 139.0,62.9 141.0,69.6 145.0,73.5 C 149.0,77.3 151.0,77.0 155.0,79.2 C 159.0,81.5 161.0,83.5 165.0,84.9 C 169.0,86.3 171.0,86.5 175.0,86.2 C 179.0,86.0 181.0,85.0 185.0,83.5 C 189.0,82.0 191.0,80.2 195.0,78.9 C 199.0,77.6 201.0,78.7 205.0,77.1 C 209.0,75.6 211.0,73.4 215.0,71.2 C 219.0,69.0 221.0,67.5 225.0,66.2 C 229.0,65.0 231.0,66.3 235.0,64.9 C 239.0,63.5 241.0,69.3 245.0,59.3 C 249.0,49.3 251.0,20.2 255.0,15.0 C 259.0,9.8 261.0,24.5 265.0,33.3 C 269.0,42.2 271.0,52.8 275.0,59.3 C 279.0,65.8 281.0,70.2 285.0,65.9 C 289.0,61.6 291.0,43.6 295.0,37.8 C 299.0,31.9 301.0,30.4 305.0,36.7 C 309.0,42.9 311.0,61.9 315.0,69.1 C 319.0,76.2 321.0,70.4 325.0,72.5 C 329.0,74.7 331.0,77.6 335.0,79.9 C 339.0,82.1 341.0,82.5 345.0,83.7 C 349.0,84.9 351.0,85.2 355.0,85.7 C 359.0,86.3 361.0,87.8 365.0,86.5 C 369.0,85.1 371.0,87.3 375.0,79.0 C 379.0,70.6 381.0,55.6 385.0,44.6 C 389.0,33.7 391.0,24.2 395.0,24.3 C 399.0,24.3 401.0,41.6 405.0,44.9 C 409.0,48.1 411.0,49.4 415.0,40.5 C 419.0,31.5 421.0,-9.7 425.0,0.0 C 429.0,9.7 431.0,72.7 435.0,88.8 C 439.0,104.9 441.0,81.0 445.0,80.4 C 449.0,79.9 451.0,85.6 455.0,86.2 C 459.0,86.8 461.0,84.8 465.0,83.2 C 469.0,81.7 471.0,78.4 475.0,78.3 C 479.0,78.3 481.0,80.8 485.0,82.9 C 489.0,84.9 491.0,88.5 495.0,88.6 C 499.0,88.7 501.0,86.9 505.0,83.5 C 509.0,80.1 511.0,75.3 515.0,71.8 C 519.0,68.2 521.0,69.5 525.0,65.6 C 529.0,61.7 531.0,60.0 535.0,52.3 C 539.0,44.6 541.0,31.0 545.0,27.1 C 549.0,23.1 551.0,27.4 555.0,32.6 C 559.0,37.8 561.0,43.8 565.0,53.0 C 569.0,62.3 571.0,73.5 575.0,78.7 C 579.0,83.9 581.0,80.6 585.0,79.1 C 589.0,77.7 591.0,71.9 595.0,71.4 C 599.0,70.8 601.0,72.9 605.0,76.3 C 609.0,79.7 611.0,85.9 615.0,88.4 C 619.0,90.9 621.0,95.8 625.0,88.9 C 629.0,82.0 631.0,53.8 635.0,53.9 C 639.0,54.0 641.0,82.0 645.0,89.3 C 649.0,96.5 651.0,89.9 655.0,90.0 C 659.0,90.1 661.0,91.7 665.0,90.0 C 669.0,88.3 671.0,83.2 675.0,81.6 C 679.0,80.0 681.0,80.5 685.0,81.8 C 689.0,83.2 691.0,88.0 695.0,88.3 C 699.0,88.7 701.0,85.6 705.0,83.5 C 709.0,81.4 711.0,78.8 715.0,78.0 C 719.0,77.2 721.0,78.3 725.0,79.3 C 729.0,80.4 731.0,84.7 735.0,83.3 C 739.0,82.0 741.0,76.2 745.0,72.5 C 749.0,68.8 751.0,63.3 755.0,64.8 C 759.0,66.3 761.0,75.9 765.0,80.0 C 769.0,84.1 771.0,84.0 775.0,85.5 C 779.0,87.0 781.0,87.2 785.0,87.5 C 789.0,87.9 791.0,86.9 795.0,87.2 C 799.0,87.5 801.0,95.6 805.0,88.9 C 809.0,82.2 811.0,53.5 815.0,53.7 C 819.0,53.9 821.0,82.7 825.0,90.0 C 829.0,97.3 831.0,90.0 835.0,90.0 C 839.0,90.0 841.0,90.0 845.0,90.0 C 849.0,90.0 851.0,90.0 855.0,90.0 C 859.0,90.0 861.0,90.0 865.0,90.0 C 869.0,90.0 871.0,90.0 875.0,90.0 C 879.0,90.0 881.0,90.0 885.0,90.0 C 889.0,90.0 891.0,90.0 895.0,90.0 C 899.0,90.0 901.0,90.0 905.0,90.0 C 909.0,90.0 911.0,90.0 915.0,90.0 C 919.0,90.0 921.0,90.3 925.0,90.0 C 929.0,89.7 931.0,88.7 935.0,88.6 C 939.0,88.5 941.0,89.1 945.0,89.4 C 949.0,89.7 951.0,89.9 955.0,90.0 C 959.0,90.1 961.0,90.0 965.0,90.0 C 969.0,90.0 971.0,90.0 975.0,90.0 C 979.0,90.0 981.0,90.0 985.0,90.0 C 989.0,90.0 992.0,90.0 995.0,90.0 C 998.0,90.0 999.0,88.0 1000.0,90.0 C 1001.0,92.0 1000.0,98.0 1000.0,100.0"
    # duration_in_seconds = 851

    # T3eEZ-_2m9w
    # d = "M 0.0,100.0 C 1.0,80.0 2.0,15.6 5.0,0.0 C 8.0,-15.6 11.0,17.1 15.0,21.9 C 19.0,26.6 21.0,23.5 25.0,23.7 C 29.0,23.9 31.0,22.7 35.0,22.7 C 39.0,22.7 41.0,23.5 45.0,23.7 C 49.0,24.0 51.0,24.1 55.0,23.8 C 59.0,23.5 61.0,22.6 65.0,22.2 C 69.0,21.8 71.0,22.0 75.0,21.8 C 79.0,21.6 81.0,21.3 85.0,21.2 C 89.0,21.1 91.0,21.5 95.0,21.4 C 99.0,21.3 101.0,20.0 105.0,20.7 C 109.0,21.4 111.0,23.6 115.0,24.9 C 119.0,26.3 121.0,26.9 125.0,27.6 C 129.0,28.3 131.0,28.5 135.0,28.6 C 139.0,28.6 141.0,27.7 145.0,27.9 C 149.0,28.2 151.0,29.2 155.0,29.8 C 159.0,30.4 161.0,30.5 165.0,30.9 C 169.0,31.4 171.0,32.0 175.0,31.9 C 179.0,31.9 181.0,30.8 185.0,30.7 C 189.0,30.5 191.0,31.2 195.0,31.3 C 199.0,31.3 201.0,31.4 205.0,30.8 C 209.0,30.3 211.0,29.1 215.0,28.4 C 219.0,27.8 221.0,27.9 225.0,27.7 C 229.0,27.5 231.0,27.3 235.0,27.5 C 239.0,27.6 241.0,28.2 245.0,28.6 C 249.0,29.0 251.0,29.0 255.0,29.7 C 259.0,30.3 261.0,31.0 265.0,31.8 C 269.0,32.6 271.0,33.2 275.0,33.7 C 279.0,34.2 281.0,33.5 285.0,34.2 C 289.0,35.0 291.0,36.1 295.0,37.3 C 299.0,38.5 301.0,39.5 305.0,40.2 C 309.0,41.0 311.0,40.7 315.0,41.1 C 319.0,41.6 321.0,42.2 325.0,42.5 C 329.0,42.7 331.0,42.2 335.0,42.2 C 339.0,42.3 341.0,42.6 345.0,42.6 C 349.0,42.6 351.0,42.5 355.0,42.1 C 359.0,41.8 361.0,41.1 365.0,40.8 C 369.0,40.6 371.0,40.9 375.0,40.8 C 379.0,40.8 381.0,40.7 385.0,40.4 C 389.0,40.1 391.0,39.5 395.0,39.4 C 399.0,39.2 401.0,39.3 405.0,39.7 C 409.0,40.1 411.0,41.0 415.0,41.4 C 419.0,41.8 421.0,41.5 425.0,41.8 C 429.0,42.2 431.0,42.4 435.0,43.2 C 439.0,44.0 441.0,45.2 445.0,46.0 C 449.0,46.7 451.0,46.6 455.0,47.0 C 459.0,47.4 461.0,47.4 465.0,47.9 C 469.0,48.4 471.0,49.0 475.0,49.3 C 479.0,49.7 481.0,49.7 485.0,49.6 C 489.0,49.5 491.0,49.2 495.0,48.9 C 499.0,48.6 501.0,48.3 505.0,48.0 C 509.0,47.8 511.0,47.8 515.0,47.7 C 519.0,47.6 521.0,47.8 525.0,47.5 C 529.0,47.2 531.0,46.3 535.0,46.0 C 539.0,45.7 541.0,45.8 545.0,46.0 C 549.0,46.1 551.0,46.6 555.0,46.8 C 559.0,47.1 561.0,46.8 565.0,47.1 C 569.0,47.5 571.0,48.3 575.0,48.7 C 579.0,49.1 581.0,49.1 585.0,49.3 C 589.0,49.5 591.0,49.7 595.0,49.7 C 599.0,49.7 601.0,49.6 605.0,49.4 C 609.0,49.2 611.0,49.5 615.0,48.8 C 619.0,48.1 621.0,47.9 625.0,45.9 C 629.0,43.9 631.0,41.4 635.0,38.9 C 639.0,36.4 641.0,34.7 645.0,33.4 C 649.0,32.2 651.0,32.5 655.0,32.5 C 659.0,32.4 661.0,33.0 665.0,33.2 C 669.0,33.5 671.0,33.4 675.0,33.6 C 679.0,33.9 681.0,33.7 685.0,34.4 C 689.0,35.0 691.0,35.8 695.0,36.9 C 699.0,37.9 701.0,37.6 705.0,39.5 C 709.0,41.4 711.0,43.9 715.0,46.3 C 719.0,48.6 721.0,49.5 725.0,51.1 C 729.0,52.8 731.0,53.5 735.0,54.6 C 739.0,55.7 741.0,56.0 745.0,56.7 C 749.0,57.4 751.0,57.6 755.0,58.2 C 759.0,58.8 761.0,59.4 765.0,59.7 C 769.0,60.1 771.0,59.6 775.0,59.9 C 779.0,60.2 781.0,60.8 785.0,61.2 C 789.0,61.5 791.0,61.3 795.0,61.7 C 799.0,62.1 801.0,62.7 805.0,63.0 C 809.0,63.3 811.0,63.1 815.0,63.2 C 819.0,63.3 821.0,63.7 825.0,63.6 C 829.0,63.4 831.0,63.5 835.0,62.5 C 839.0,61.5 841.0,60.0 845.0,58.5 C 849.0,57.0 851.0,55.8 855.0,54.9 C 859.0,54.1 861.0,54.1 865.0,54.2 C 869.0,54.2 871.0,54.6 875.0,55.2 C 879.0,55.7 881.0,56.2 885.0,56.9 C 889.0,57.5 891.0,57.3 895.0,58.2 C 899.0,59.1 901.0,60.0 905.0,61.1 C 909.0,62.3 911.0,62.7 915.0,64.1 C 919.0,65.6 921.0,66.6 925.0,68.4 C 929.0,70.3 931.0,71.9 935.0,73.5 C 939.0,75.2 941.0,75.3 945.0,76.6 C 949.0,77.8 951.0,78.6 955.0,79.8 C 959.0,80.9 961.0,81.3 965.0,82.4 C 969.0,83.5 971.0,83.7 975.0,85.3 C 979.0,86.8 981.0,89.1 985.0,90.0 C 989.0,90.9 992.0,90.0 995.0,90.0 C 998.0,90.0 999.0,88.0 1000.0,90.0 C 1001.0,92.0 1000.0,98.0 1000.0,100.0"
    # duration_in_seconds = 145

    points, maxima_points, timestamp_points = process_heatmap_to_highlight_point(d, duration_in_seconds)

    if show_on_graph:
        visualize(points, maxima_points, timestamp_points, duration_in_seconds)

    return np.column_stack((timestamp_points * duration_in_seconds, maxima_points[:, 1]))


def main():
    parser = argparse.ArgumentParser(description="Get most watched timestamp from YouTube video heatmap")
    parser.add_argument("video_id", help="YouTube video ID")
    args = parser.parse_args()

    video_id = args.video_id
    print(f"🎬 Processing video_id: {video_id}")

    mwt = get_most_watched_timestamp(video_id)
    print(mwt)

    print("col 1 is timestamp, col 2 is highlight score")


if __name__ == "__main__":
    main()
