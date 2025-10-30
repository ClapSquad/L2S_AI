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


def time_to_seconds(time_str: str) -> float:
    parts = [int(p) for p in time_str.split(":")]
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0, *parts
    else:
        return 0
    return h * 3600 + m * 60 + s


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


def get_most_watched_timestamp(video_id: str):
    # path_html, video_duration = get_heatmap_path_and_duration(video_id)
    # if path_html:
    #     print("✅ Heatmap found")
    # else:
    #     print("❌ Heatmap not found")
    # d = get_d_from_path(path_html)
    # duration_in_seconds = time_to_seconds(video_duration)
    d = "M 0.0,100.0 C 1.0,80.0 2.0,15.6 5.0,0.0 C 8.0,-15.6 11.0,17.1 15.0,21.9 C 19.0,26.6 21.0,23.5 25.0,23.7 C 29.0,23.9 31.0,22.7 35.0,22.7 C 39.0,22.7 41.0,23.5 45.0,23.7 C 49.0,24.0 51.0,24.1 55.0,23.8 C 59.0,23.5 61.0,22.6 65.0,22.2 C 69.0,21.8 71.0,22.0 75.0,21.8 C 79.0,21.6 81.0,21.3 85.0,21.2 C 89.0,21.1 91.0,21.5 95.0,21.4 C 99.0,21.3 101.0,20.0 105.0,20.7 C 109.0,21.4 111.0,23.6 115.0,24.9 C 119.0,26.3 121.0,26.9 125.0,27.6 C 129.0,28.3 131.0,28.5 135.0,28.6 C 139.0,28.6 141.0,27.7 145.0,27.9 C 149.0,28.2 151.0,29.2 155.0,29.8 C 159.0,30.4 161.0,30.5 165.0,30.9 C 169.0,31.4 171.0,32.0 175.0,31.9 C 179.0,31.9 181.0,30.8 185.0,30.7 C 189.0,30.5 191.0,31.2 195.0,31.3 C 199.0,31.3 201.0,31.4 205.0,30.8 C 209.0,30.3 211.0,29.1 215.0,28.4 C 219.0,27.8 221.0,27.9 225.0,27.7 C 229.0,27.5 231.0,27.3 235.0,27.5 C 239.0,27.6 241.0,28.2 245.0,28.6 C 249.0,29.0 251.0,29.0 255.0,29.7 C 259.0,30.3 261.0,31.0 265.0,31.8 C 269.0,32.6 271.0,33.2 275.0,33.7 C 279.0,34.2 281.0,33.5 285.0,34.2 C 289.0,35.0 291.0,36.1 295.0,37.3 C 299.0,38.5 301.0,39.5 305.0,40.2 C 309.0,41.0 311.0,40.7 315.0,41.1 C 319.0,41.6 321.0,42.2 325.0,42.5 C 329.0,42.7 331.0,42.2 335.0,42.2 C 339.0,42.3 341.0,42.6 345.0,42.6 C 349.0,42.6 351.0,42.5 355.0,42.1 C 359.0,41.8 361.0,41.1 365.0,40.8 C 369.0,40.6 371.0,40.9 375.0,40.8 C 379.0,40.8 381.0,40.7 385.0,40.4 C 389.0,40.1 391.0,39.5 395.0,39.4 C 399.0,39.2 401.0,39.3 405.0,39.7 C 409.0,40.1 411.0,41.0 415.0,41.4 C 419.0,41.8 421.0,41.5 425.0,41.8 C 429.0,42.2 431.0,42.4 435.0,43.2 C 439.0,44.0 441.0,45.2 445.0,46.0 C 449.0,46.7 451.0,46.6 455.0,47.0 C 459.0,47.4 461.0,47.4 465.0,47.9 C 469.0,48.4 471.0,49.0 475.0,49.3 C 479.0,49.7 481.0,49.7 485.0,49.6 C 489.0,49.5 491.0,49.2 495.0,48.9 C 499.0,48.6 501.0,48.3 505.0,48.0 C 509.0,47.8 511.0,47.8 515.0,47.7 C 519.0,47.6 521.0,47.8 525.0,47.5 C 529.0,47.2 531.0,46.3 535.0,46.0 C 539.0,45.7 541.0,45.8 545.0,46.0 C 549.0,46.1 551.0,46.6 555.0,46.8 C 559.0,47.1 561.0,46.8 565.0,47.1 C 569.0,47.5 571.0,48.3 575.0,48.7 C 579.0,49.1 581.0,49.1 585.0,49.3 C 589.0,49.5 591.0,49.7 595.0,49.7 C 599.0,49.7 601.0,49.6 605.0,49.4 C 609.0,49.2 611.0,49.5 615.0,48.8 C 619.0,48.1 621.0,47.9 625.0,45.9 C 629.0,43.9 631.0,41.4 635.0,38.9 C 639.0,36.4 641.0,34.7 645.0,33.4 C 649.0,32.2 651.0,32.5 655.0,32.5 C 659.0,32.4 661.0,33.0 665.0,33.2 C 669.0,33.5 671.0,33.4 675.0,33.6 C 679.0,33.9 681.0,33.7 685.0,34.4 C 689.0,35.0 691.0,35.8 695.0,36.9 C 699.0,37.9 701.0,37.6 705.0,39.5 C 709.0,41.4 711.0,43.9 715.0,46.3 C 719.0,48.6 721.0,49.5 725.0,51.1 C 729.0,52.8 731.0,53.5 735.0,54.6 C 739.0,55.7 741.0,56.0 745.0,56.7 C 749.0,57.4 751.0,57.6 755.0,58.2 C 759.0,58.8 761.0,59.4 765.0,59.7 C 769.0,60.1 771.0,59.6 775.0,59.9 C 779.0,60.2 781.0,60.8 785.0,61.2 C 789.0,61.5 791.0,61.3 795.0,61.7 C 799.0,62.1 801.0,62.7 805.0,63.0 C 809.0,63.3 811.0,63.1 815.0,63.2 C 819.0,63.3 821.0,63.7 825.0,63.6 C 829.0,63.4 831.0,63.5 835.0,62.5 C 839.0,61.5 841.0,60.0 845.0,58.5 C 849.0,57.0 851.0,55.8 855.0,54.9 C 859.0,54.1 861.0,54.1 865.0,54.2 C 869.0,54.2 871.0,54.6 875.0,55.2 C 879.0,55.7 881.0,56.2 885.0,56.9 C 889.0,57.5 891.0,57.3 895.0,58.2 C 899.0,59.1 901.0,60.0 905.0,61.1 C 909.0,62.3 911.0,62.7 915.0,64.1 C 919.0,65.6 921.0,66.6 925.0,68.4 C 929.0,70.3 931.0,71.9 935.0,73.5 C 939.0,75.2 941.0,75.3 945.0,76.6 C 949.0,77.8 951.0,78.6 955.0,79.8 C 959.0,80.9 961.0,81.3 965.0,82.4 C 969.0,83.5 971.0,83.7 975.0,85.3 C 979.0,86.8 981.0,89.1 985.0,90.0 C 989.0,90.9 992.0,90.0 995.0,90.0 C 998.0,90.0 999.0,88.0 1000.0,90.0 C 1001.0,92.0 1000.0,98.0 1000.0,100.0"
    duration_in_seconds = 145
    visualize(d, duration_in_seconds)


def visualize(d_attr: str, duration_in_seconds):
    def parse_path_to_points(d_attr):
        """SVG path에서 (x, y) 좌표 추출"""
        points = re.findall(r"([0-9.]+),([\-0-9.]+)", d_attr)
        return np.array([(float(x), float(y)) for x, y in points])

    def find_local_minima(points):
        """numpy만으로 local minima (heatmap 피크) 찾기"""
        y = points[:, 1]
        x = points[:, 0]

        dy_prev = np.roll(y, 1)
        dy_next = np.roll(y, -1)

        minima_mask = (y < dy_prev) & (y < dy_next)
        minima_mask[0] = minima_mask[-1] = False  # 양끝 제외

        return points[minima_mask]

    def compute_relative_positions(minima_points, points):
        """전체 x범위 대비 몇 % 지점인지 계산"""
        min_x, max_x = points[:, 0].min(), points[:, 0].max()
        ratios = (minima_points[:, 0] - min_x) / (max_x - min_x)
        return ratios


    # 🔹 데이터 파싱 및 피크 검출
    points = parse_path_to_points(d_attr)
    minima_points = find_local_minima(points)
    ratios = compute_relative_positions(minima_points, points)

    print("📉 Local minima (heatmap peaks):")
    for (x, y), r in zip(minima_points, ratios):
        print(f"x={x:.1f}, y={y:.1f} → 전체 x의 {100 * r:.2f}%, timestamp={r * duration_in_seconds:.1f}")

    # 🔹 시각화
    plt.figure(figsize=(10, 5))
    plt.plot(points[:, 0], points[:, 1], label="Heatmap Curve")  # heatmap 곡선
    plt.scatter(minima_points[:, 0], minima_points[:, 1], color='red', s=50, label="Peaks (local minima)")  # 피크 표시
    plt.gca().invert_yaxis()  # YouTube SVG는 y축이 아래로 향하므로 반전

    plt.title("YouTube Heatmap Path Visualization")
    plt.xlabel("X (Progress along video)")
    plt.ylabel("Y (View density)")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    get_most_watched_timestamp("T3eEZ-_2m9w")
