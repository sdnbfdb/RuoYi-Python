r"""
视频→ASCII终端动画播放器
提取视频帧 → ASCII字符画 → 终端逐帧播放
用法: python video_to_ascii_animation.py [视频路径]
"""
import os
import sys
import time
import cv2
import numpy as np
from scipy import ndimage

# ========== 配置参数 ==========
CHAR_WIDTH = 90        # 终端输出宽度（字符数）
HEIGHT_RATIO = 0.45    # 纵向压缩比
BLOCK_SIZE = 2         # 像素块粒度
DARK_THRESH = 128      # 暗像素判定值
SOLID_THRESH = 0.93    # ≥93%暗像素才用*（大幅提高，避免全屏*）
EMPTY_THRESH = 0.08    # ≤8%暗像素直接留空（背景透明）
FRAME_INTERVAL = 0.5   # 视频帧提取间隔（秒）
FRAME_DELAY = 0.10     # 播放帧间隔（秒）
LOOP_COUNT = 0         # 0=无限循环，按Ctrl+C停止

# 默认视频路径
DEFAULT_VIDEO = r"C:\Users\sanjin\Desktop\tupian\bfc6967a25e30ebb9286a4c09c1569ae.mp4"


def extract_frames_in_memory(video_path, interval_seconds=FRAME_INTERVAL):
    """从视频提取帧到内存（numpy数组），不写磁盘"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"视频: FPS={fps:.0f}  总帧={total_frames}  时长={duration:.0f}s", flush=True)

    frame_step = int(fps * interval_seconds) if fps > 0 else 1
    indices = list(range(0, total_frames, max(1, frame_step)))
    print(f"提取间隔={interval_seconds}s → 共 {len(indices)} 帧", flush=True)

    frames = []
    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append(gray)
        print(f"\r  提取帧 {i+1}/{len(indices)}", end='', flush=True)

    cap.release()
    print(f"\n提取完成: {len(frames)} 帧", flush=True)
    return frames


def resize_frame(gray, char_width=CHAR_WIDTH):
    """缩放灰度帧到目标尺寸"""
    h, w = gray.shape
    new_w = char_width * BLOCK_SIZE
    new_h = int(new_w * (h / w) * HEIGHT_RATIO)
    new_h = max((new_h // BLOCK_SIZE) * BLOCK_SIZE, BLOCK_SIZE)
    return cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)


def compute_edge_directions(img_array):
    """Sobel边缘检测，返回梯度方向矩阵"""
    gx = ndimage.sobel(img_array.astype(float), axis=1)
    gy = ndimage.sobel(img_array.astype(float), axis=0)
    gx_abs, gy_abs = np.abs(gx), np.abs(gy)
    gx_sign, gy_sign = np.sign(gx), np.sign(gy)

    direction = np.zeros_like(img_array, dtype=int)
    mask_h = gy_abs > gx_abs * 2.0
    direction[mask_h] = 0   # '-'
    mask_v = gx_abs > gy_abs * 2.0
    direction[mask_v] = 1   # '|'
    mask_d = (~mask_h) & (~mask_v) & ((gx_abs > 0) | (gy_abs > 0))
    direction[mask_d & (gx_sign * gy_sign >= 0)] = 2  # '/'
    direction[mask_d & (gx_sign * gy_sign < 0)] = 3   # '\'
    return direction


def frame_to_ascii_lines(img_array, dir_map):
    """将灰度帧+方向图转为ASCII行列表（自适应暗/亮背景，强力去噪）"""
    h, w = img_array.shape
    h_cells = h // BLOCK_SIZE
    w_cells = w // BLOCK_SIZE
    DIR_CHARS = ['-', '|', '/', '\\']

    # 计算梯度强度图
    gx = ndimage.sobel(img_array.astype(float), axis=1)
    gy = ndimage.sobel(img_array.astype(float), axis=0)
    gradient_mag = np.sqrt(gx**2 + gy**2)
    GRAD_MIN = 70  # 梯度门槛降低，保留更多弱边缘细节

    # 自适应检测
    mean_brightness = np.mean(img_array)
    inverted = mean_brightness < 80
    if inverted:
        fill_thresh = 0.95   # 极严格：95%亮像素才用*
        blank_thresh = 0.28  # <28%直接留空（大幅收窄半填充区间）
    else:
        fill_thresh = SOLID_THRESH
        blank_thresh = EMPTY_THRESH

    lines = []
    for cy in range(h_cells):
        line = []
        for cx in range(w_cells):
            y0, y1 = cy * BLOCK_SIZE, (cy + 1) * BLOCK_SIZE
            x0, x1 = cx * BLOCK_SIZE, (cx + 1) * BLOCK_SIZE
            block = img_array[y0:y1, x0:x1]
            grad_block = gradient_mag[y0:y1, x0:x1]

            if inverted:
                ratio = np.sum(block >= DARK_THRESH) / block.size
            else:
                ratio = np.sum(block < DARK_THRESH) / block.size

            if ratio >= fill_thresh:
                line.append('*')
            elif ratio <= blank_thresh:
                line.append(' ')
            else:
                avg_grad = np.mean(grad_block)
                if avg_grad < GRAD_MIN:
                    line.append(' ')
                else:
                    dir_block = dir_map[y0:y1, x0:x1]
                    dir_counts = np.bincount(dir_block.flatten(), minlength=4)
                    best_dir = int(np.argmax(dir_counts))
                    line.append(DIR_CHARS[best_dir])
        lines.append(''.join(line))
    return lines


def denoise_lines(lines):
    """连通区域面积过滤：删除所有小于 MIN_AREA 的字符块（彻底去噪）"""
    if not lines:
        return []
    grid = [list(line) for line in lines]
    rows = len(grid)
    cols = max(len(r) for r in grid)
    for r in grid:
        while len(r) < cols:
            r.append(' ')

    visited = [[False] * cols for _ in range(rows)]
    MIN_AREA = 10  # 连通区域至少10个字符才保留（保留小动作细节）

    def flood(y, x, target):
        """BFS填充，返回该连通区域的坐标列表"""
        stack = [(y, x)]
        region = []
        while stack:
            cy, cx = stack.pop()
            if cy < 0 or cy >= rows or cx < 0 or cx >= cols:
                continue
            if visited[cy][cx]:
                continue
            ch = grid[cy][cx]
            if ch == ' ':
                continue
            # 同组判定：*算实体，-|\/算边缘
            is_target = (target == '*' and ch == '*') or (target != '*' and ch != '*')
            if not is_target:
                continue
            visited[cy][cx] = True
            region.append((cy, cx))
            for dy, dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
                stack.append((cy+dy, cx+dx))
        return region

    # 找所有连通区域，标记要删除的小区域
    to_remove = set()
    for y in range(rows):
        for x in range(cols):
            if visited[y][x] or grid[y][x] == ' ':
                continue
            region = flood(y, x, grid[y][x])
            if len(region) < MIN_AREA:
                for ry, rx in region:
                    to_remove.add((ry, rx))

    # 清除小区域
    for y, x in to_remove:
        grid[y][x] = ' '

    return [''.join(row).rstrip() for row in grid]


def crop_art(lines):
    """裁剪+去噪"""
    lines = denoise_lines(lines)
    while lines and lines[0].strip() == '':
        lines.pop(0)
    while lines and lines[-1].strip() == '':
        lines.pop()
    if not lines:
        return []

    min_lead = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
    lines = [l[min_lead:] for l in lines]
    max_len = max(len(l.rstrip()) for l in lines)
    lines = [l[:max_len] for l in lines]
    return lines


def clear_screen():
    """清屏 - VS Code 终端兼容方案"""
    import sys
    # \033[2J = 清可见区域  \033[3J = 清滚动缓冲区  \033[H = 光标归位
     sys.stdout.write('\033[2J\033[3J\033[H')
    sys.stdout.flush()


def play_animation(frames, loop=LOOP_COUNT, delay=FRAME_DELAY):
    """终端逐帧播放ASCII动画"""
    if not frames:
        print("没有帧可播放")
        return

    max_w = max(max(len(l) for l in f) for f in frames)
    max_h = max(len(f) for f in frames)
    padded = []
    for f in frames:
        lines = [l + ' ' * (max_w - len(l)) for l in f]
        pad_top = (max_h - len(lines)) // 2
        pad_bot = max_h - len(lines) - pad_top
        padded.append([''] * pad_top + lines + [''] * pad_bot)

    try:
        import shutil
        term_w, term_h = shutil.get_terminal_size()
    except Exception:
        term_w, term_h = 80, 24

    side_pad = max(0, (term_w - max_w) // 2)
    side_space = ' ' * side_pad
    top_pad = max(0, (term_h - max_h) // 2 - 1)

    total = len(padded)
    loop_label = "无限" if loop == 0 else str(loop)
    print(f"\n准备播放: {total} 帧, 循环 {loop_label}, 按 Ctrl+C 停止...")
    time.sleep(0.8)

    cycle = 0
    import sys
    # 隐藏光标，避免闪烁
    sys.stdout.write('\033[?25l')
    sys.stdout.flush()
    try:
        while loop == 0 or cycle < loop:
            for frame in padded:
                # 回到屏幕左上角，直接覆盖旧内容
                sys.stdout.write('\x1b[H')
                # 顶部填充
                for _ in range(top_pad):
                    sys.stdout.write('\r\n')
                # 打印帧内容（每行填充到终端宽度，确保完全覆盖旧内容）
                for line in frame:
                    text = side_space + line
                    # 用空格填充到终端宽度，防止旧内容残留
                    if len(text) < term_w:
                        text += ' ' * (term_w - len(text))
                    sys.stdout.write(text + '\r\n')
                # 覆盖剩余行（防止旧内容残留）
                remaining = max(0, term_h - top_pad - len(frame))
                for _ in range(remaining):
                    sys.stdout.write(' ' * term_w + '\r\n')
                sys.stdout.flush()
                time.sleep(delay)
            cycle += 1
    except KeyboardInterrupt:
        pass
    finally:
        # 显示光标
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()
        print("动画结束")


def main():
    import sys
    video_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO

    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}")
        print(f"用法: python {os.path.basename(__file__)} <视频路径>")
        sys.exit(1)

    print("=" * 50, flush=True)
    print("视频→ASCII终端动画播放器", flush=True)
    print("=" * 50, flush=True)
    print(f"输入: {video_path}", flush=True)

    # 步骤1: 提取视频帧
    print("\n[1/3] 提取视频帧...", flush=True)
    gray_frames = extract_frames_in_memory(video_path, FRAME_INTERVAL)
    if not gray_frames:
        print("错误: 未能提取任何帧")
        sys.exit(1)

    # 步骤2: 转换为ASCII
    # 先检测第一帧亮度，确定渲染模式
    first_resized = resize_frame(gray_frames[0], CHAR_WIDTH)
    first_brightness = np.mean(first_resized)
    auto_mode = "暗底亮字" if first_brightness < 80 else "亮底暗字"
    print(f"\n[2/3] 转换 {len(gray_frames)} 帧为ASCII (模式: {auto_mode}, 均值亮度={first_brightness:.0f})...", flush=True)
    ascii_frames = []
    for i, gray in enumerate(gray_frames):
        resized = resize_frame(gray, CHAR_WIDTH)
        dir_map = compute_edge_directions(resized)
        lines = frame_to_ascii_lines(resized, dir_map)
        lines = crop_art(lines)
        if lines:
            ascii_frames.append(lines)
        print(f"\r  转换帧 {i+1}/{len(gray_frames)}", end='', flush=True)

    print(f"\n转换完成: {len(ascii_frames)} 帧", flush=True)

    if not ascii_frames:
        print("错误: 没有成功转换任何帧")
        sys.exit(1)

    # 步骤3: 终端播放
    print(f"\n[3/3] 终端播放...", flush=True)
    play_animation(ascii_frames)

    input('\n按 Enter 键退出...')


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        input('\n按 Enter 键退出...')
