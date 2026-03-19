import cv2
from tkinter import Tk, filedialog


def select_video_file():
    root = Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select a video file",
        filetypes=[
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return path


def view_frames(video_path=None):
    if not video_path:
        video_path = select_video_file()
    if not video_path:
        print("No file selected. Exiting.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: could not open video '{video_path}'")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"\nTotal frames: {total_frames}")
    print("\nControls (press keys while OpenCV window is focused):")
    print("  'd' or '.' = Next frame")
    print("  'a' or ',' = Previous frame")
    print("  'n' = Jump forward 10 frames")
    print("  'p' = Jump back 10 frames")
    print("  'j' = Jump to specific frame")
    print("  'q' = Quit")
    print("\nNote: Arrow keys may not work on all systems, use letter keys instead\n")
    
    frame_num = 0
    window_name = 'Video Frame Viewer'
    
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if ret:
            # Add frame number text on the image
            display_frame = frame.copy()
            cv2.putText(display_frame, f'Frame: {frame_num}/{total_frames-1}', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow(window_name, display_frame)
        else:
            print(f"Error reading frame {frame_num}")
            break
        
        key = cv2.waitKey(0) & 0xFF  # Mask to get only the lower 8 bits
        
        if key == ord('q'):  # Quit
            print("Quitting...")
            break
        elif key == ord('d') or key == ord('.'):  # Next frame
            frame_num = min(frame_num + 1, total_frames - 1)
            print(f"Frame {frame_num}")
        elif key == ord('a') or key == ord(','):  # Previous frame
            frame_num = max(frame_num - 1, 0)
            print(f"Frame {frame_num}")
        elif key == ord('n'):  # Jump forward 10 frames
            frame_num = min(frame_num + 10, total_frames - 1)
            print(f"Frame {frame_num}")
        elif key == ord('p'):  # Jump back 10 frames
            frame_num = max(frame_num - 10, 0)
            print(f"Frame {frame_num}")
        elif key == ord('j'):  # Jump to specific frame
            cv2.destroyAllWindows()  # Close window before terminal input
            try:
                new_frame = int(input(f"Enter frame number (0-{total_frames-1}): "))
                frame_num = max(0, min(new_frame, total_frames - 1))
                print(f"Jumping to frame {frame_num}")
            except ValueError:
                print("Invalid input, staying at current frame")
        else:
            print(f"Unknown key code: {key}. Press keys while OpenCV window is focused.")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    view_frames()