import os
from datetime import timedelta
import regex
import argparse


class CueHeader:
    title = "Time Calculator Output"
    file = ""
    out_format = "WAVE"
    performer = "No performer"
    duration_in_frames = 0


class CueTime:
    minutes = 0
    seconds = 0
    frames = 0  # note each frame is 1/75th of a sec in cue sheets

    def __init__(self, tot_frames: int):
        self.minutes = int(tot_frames / (60 * 75))
        remainder = tot_frames - (self.minutes * 60 * 75)
        self.seconds = int(remainder / 75)
        remainder2 = tot_frames - (self.seconds * 75) - (self.minutes * 60 * 75)
        self.frames = int(remainder2)

    @property
    def total_frames(self) -> int:
        total = self.frames + (75 * self.seconds) + (75 * 60) * self.minutes
        return total

    @property
    def total_seconds(self) -> int:  # note this truncates the frames
        return self.minutes * 60 + self.seconds


class TimeString:
    hours = 0
    minutes = 0
    seconds = 0

    def __init__(self, in_string: str):
        # in_string will either be of the form '1h22m33s' or '1:22:33' or possible '1.22.33
        pattern = r"[:,.-]"
        punctuation = ":,.-"
        if any(char in in_string for char in punctuation):
            bits = regex.split(pattern, in_string)
            if len(bits) >= 3:  # must include hours
                self.hours = int(bits[0])
                self.minutes = int(bits[1])
                self.seconds = int(bits[2])
            else:
                self.hours = 0
                self.minutes = int(bits[0])
                self.seconds = int(bits[1])
        else:
            pattern = r"(\d+)(h|m|s)"
            matches = regex.finditer(pattern=pattern, string=in_string)
            if matches:
                for match in matches:
                    num = int(match.group(1))
                    unit = match.group(2)
                    if unit == "h":
                        self.hours = num
                    elif unit == "m":
                        self.minutes = num
                    else:
                        self.seconds = int(num)

    def to_string(self) -> str:
        if self.hours == 0 and self.minutes == 0:
            return f"{self.seconds:.0f}s"
        if self.hours == 0:
            return f"{self.minutes:.0f}m {self.seconds:.0f}s"
        return f"{self.hours:.0f}h {self.minutes:.0f}m {self.seconds:.0f}s"

    def add_other(self, other_ts):
        my_time = timedelta(
            hours=self.hours, minutes=self.minutes, seconds=self.seconds
        )
        delta = timedelta(
            hours=other_ts.hours, minutes=other_ts.minutes, seconds=other_ts.seconds
        )
        my_time = my_time + delta
        # Get the total seconds
        total_seconds = my_time.total_seconds()
        # Calculate the hours, minutes, and seconds
        self.hours = total_seconds // 3600
        self.minutes = (total_seconds % 3600) // 60
        self.seconds = total_seconds % 60

    def sub_other(self, other_ts):
        my_time = timedelta(
            hours=self.hours, minutes=self.minutes, seconds=self.seconds
        )
        delta = timedelta(
            hours=other_ts.hours, minutes=other_ts.minutes, seconds=other_ts.seconds
        )
        my_time = my_time - delta
        # Get the total seconds
        total_seconds = my_time.total_seconds()
        # Calculate the hours, minutes, and seconds
        self.hours = total_seconds // 3600
        self.minutes = (total_seconds % 3600) // 60
        self.seconds = total_seconds % 60


class CueTrack:
    order = 0
    title = ""
    index = CueTime(0)
    offset = ""
    color = "cyan"
    duration_in_frames = 0

    def __init__(self, order: int, title: str, a_time: TimeString):
        self.order = order
        self.title = title
        total_seconds = a_time.hours * 60 * 60 + a_time.minutes * 60 + a_time.seconds
        total_frames = total_seconds * 75
        self.index = CueTime(tot_frames=total_frames)


# globals
total_ts = TimeString("0h 0m 0s")
# last_value = TimeString('0h 0m 0s')
tape = []
cue_tracks = []
order = 1


def make_tape() -> str:
    global tape
    text = "\n".join(tape)
    print(text)
    return text


def make_cuefile() -> str:
    global cue_tracks
    if not cue_tracks:
        return ""
    header = CueHeader()
    accumulator = ""
    accumulator += f'TITLE "{header.title}"\n'
    accumulator += f'FILE "{header.file}" {header.out_format}\n'
    if header.performer:
        accumulator += 'PERFORMER "' + header.performer + '"' + "\n"
    track_count = 1
    for track in cue_tracks:
        accumulator += f"  TRACK {str(track_count):02} AUDIO\n"
        accumulator += f'    TITLE "{track.title}"\n'
        accumulator += f"	 INDEX 01 {track.index.minutes:02}:{track.index.seconds:02}:{track.index.frames:02}\n"
        if track.offset:
            accumulator += f"	 REM OFFSET {track.offset}" + "\n"
        accumulator += f"	 REM COLOR {track.color}" + "\n"
        track_count += 1
    return accumulator


def save_cuefile(outfile: str):
    cues = make_cuefile()
    lines = cues.split("\n")
    with open(outfile, "w") as cuefile:
        for line in lines:
            cuefile.write(line + "\n")


def save_tapefile():
    text = make_tape()
    with open(os.path.join(".", "time-calc-tape.txt"), "w") as tapefile:
        tapefile.write(text)


# Configure window background color
def main():
    global cue_tracks, order, total_ts
    parser = argparse.ArgumentParser(description="Process input parameters.")

    # Filename parameter
    parser.add_argument(
        "-f", "--filename", type=str, help="Input file name with .txt extension"
    )

    # Starting time parameter
    parser.add_argument(
        "-s",
        "--start_time",
        type=str,
        help="Starting time in minutes and seconds (e.g., 02:30)",
        required=False,
    )

    # Output file parameter
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file name with .cue extension",
        required=False,
    )

    # padding time
    parser.add_argument(
        "-p",
        "--padding",
        type=int,
        help="Additional time (in millisecs) between cues",
        required=False,
    )

    args = parser.parse_args()

    # Accessing the parameter values
    filename = args.filename
    # start_time = args.start_time
    output_file = args.output

    # process the file
    with open(filename, "r") as inputfile:
        lines = inputfile.readlines()
        # line should have format: ChapterName|hh:mm:ss
        padding_offset = 0
        for line in lines:
            order += 1
            title, duration = line.split("|")
            cue_tracks.append(CueTrack(order, title, total_ts))
            clean_duration = duration.strip()
            timestr = TimeString(clean_duration)
            total_ts.add_other(timestr)
        total_ts.sub_other(
            TimeString("00:00:30")
        )  # fudge so we're not right at the end of audio.
        cue_tracks.append(CueTrack(order + 1, "END", total_ts))
        save_cuefile(output_file)


if __name__ == "__main__":
    main()
