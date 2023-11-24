# generate cue file from list of MP3 files.

import os
from mutagen.mp3 import MP3
from datetime import timedelta
import argparse

class CueHeader:
	title = "GeneratedOutput"
	file = ""
	out_format = "WAVE"
	performer = "Performer"
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


class CueTrack:
	order = 0
	title = ""
	index = CueTime(0)
	offset = ""
	color = "cyan"
	duration_in_frames = 0
 
	def __init__(self, order:int, timespan:timedelta):
		self.order = order
		self.title = f'XXXX{order}'
		total_seconds = timespan.total_seconds()
		total_frames = int(total_seconds * 75)
		self.index = CueTime(tot_frames=total_frames)

cue_tracks = []
fudge_time = 100 # fudge time in milliseconds

# Iterate over each file in the directory
def generate_cue_tracks(directory):
	global cue_tracks
	cue_tracks.append(CueTrack(1, timedelta(seconds=0)))
	total_millisecs = 0
	order = 2  # we've already put in the first cue track, starting from zero time
	file_names = sorted(os.listdir(directory))
	for filename in file_names:
		if filename.endswith('.mp3'):
			file_path = os.path.join(directory, filename)
			audio = MP3(file_path)
			duration = int(audio.info.length * 1000)  # gives us milliseconds
			print(f"File: {filename}, Duration: {int(duration/1000)} seconds")
			total_millisecs += (duration + fudge_time)
			track_start = timedelta(milliseconds=total_millisecs)
			track = CueTrack(order, track_start)
			cue_tracks.append(track)
			order += 1


def make_cuefile() -> str:
	global cue_tracks
	if not cue_tracks:
		return ""
	header = CueHeader()
	accumulator = ""
	accumulator += 'TITLE "' + header.title + '"' + '\n'
	accumulator += 'FILE "' + header.file + '"' + ' ' + header.out_format + '\n'
	if header.performer:
		accumulator += 'PERFORMER "' + header.performer + '"' + '\n'
	track_count = 1
	for track in cue_tracks:
		accumulator += '  TRACK ' + str(track_count).zfill(2) + ' AUDIO' + '\n'
		accumulator += '    TITLE "' + track.title + '"' + '\n'
		accumulator += '    INDEX 01 ' + str(track.index.minutes).zfill(2) + ':' + str(track.index.seconds).zfill(2) + ':' + str(track.index.frames).zfill(2) + '\n'
		if track.offset:
			accumulator += '    REM OFFSET ' + track.offset + '\n'
		accumulator += '    REM COLOR ' + track.color + '\n'
		track_count += 1
	return accumulator


def save_cuefile(output_file:str):
	cues = make_cuefile()
	lines = cues.split('\n')
	with open(output_file, 'w') as cuefile:
		for line in lines:
			cuefile.write(line + '\n')
		

def main():
	global fudge_time
	# Create the argument parser
	parser = argparse.ArgumentParser(description='Calculate MP3 file durations and create a matching CUE file')

	# Add the arguments
	parser.add_argument('directory', type=str, help='Directory containing the MP3 files')
	parser.add_argument('output_file', type=str, help='Name of the output CUE file')
	parser.add_argument('-f', '--fudge', type=int, help='Added time between tracks in millisecs', default=100, required=False)


	# Parse the arguments
	args = parser.parse_args()
	if args.fudge:
		fudge_time = args.fudge

	generate_cue_tracks(args.directory)
	save_cuefile(args.output_file)
	

if __name__ == '__main__':
	main()