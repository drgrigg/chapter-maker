#!/usr/bin/env python3

import os
import regex
import wave
import contextlib
from typing import Tuple


class CueHeader:
	title = ""
	file = ""
	out_format = ""
	performer = ""
	duration_in_frames = 0


class CueTime:
	hours = 0
	minutes = 0
	seconds = 0
	frames = 0  # note each frame is 1/75th of a sec in cue sheets

	def __init__(self, tot_frames: int):
		total_seconds = tot_frames / 75
		self.hours = int(total_seconds/3600)
		self.minutes = int((total_seconds % 3600) / 60)
		self.seconds = total_seconds % 60
		self.frames = tot_frames % 75

	@property
	def total_frames(self) -> int:
		total = self.frames + (75 * self.seconds) + (75 * 60) * self.minutes + (75 * 60 * 60) * self.hours
		return total

	@property
	def total_seconds(self) -> int:  # note this truncates the frames
		return self.hours * 60 * 60 + self.minutes * 60 + self.seconds


class CueTrack:
	order = 0
	title = ""
	index = CueTime(0)
	offset = ""
	color = ""
	duration_in_frames = 0


def get_quoted_string(line: str) -> str:
	match = regex.search(r'"(.*?)"', line)
	if match:
		return match.group(1)
	else:
		return ""


def get_duration(fname: str) -> float:
	try:
		with contextlib.closing(wave.open(fname, 'r')) as f:
			frames = f.getnframes()
			rate = f.getframerate()
			duration = frames / float(rate)
			return duration
	except Exception as ex:
		return 0.0


def file_is_ok(afile) -> bool:
	if not os.path.exists(afile):
		# print("Error: this file does not exist: " + afile)
		return False
	elif not os.path.isfile(afile):
		# print("Error: this is not a file: " + afile)
		return False
	return True


def get_file_and_format(line: str) -> Tuple[str, str]:
	match = regex.search(r'"(.*?)" (.*?)$', line)
	if match:
		return match.group(1), match.group(2)
	else:
		return get_quoted_string(line), ""


def get_wave_source(cuefile: str) -> str:
	# read header to get the source file name
	try:
		fileobject = open(cuefile, "r", encoding="utf-8")
	except IOError:
		print("Could not open " + cuefile)
		return ""

	try:
		alltext = fileobject.read()
	except UnicodeDecodeError:
		print("Could not read " + cuefile)
		return ""

	fileobject.close()

	lines = alltext.splitlines(False)
	# read header lines, stop when we hit a track
	line_num = 0
	while line_num < len(lines):
		line = lines[line_num]
		if "FILE" in line:
			fi, fo = get_file_and_format(line)
			return fi
		line_num += 1
	return ""


def get_cuetime(line: str) -> CueTime:
	ctime = CueTime(0)
	# assume input is from cue file
	# str_hours = "0"
	str_minutes = "0"
	str_seconds = "0"
	str_frames = "0"
	match = regex.search(r'INDEX 01 (\d+):(\d+):(\d+)', line)
	if match:
		str_minutes = match.group(1)
		str_seconds = match.group(2)
		str_frames = match.group(3)
	try:
		ctime.minutes = int(str_minutes)
		if ctime.minutes > 60:
			ctime.hours = int(ctime.minutes/60)
			ctime.minutes = ctime.minutes % 60
		ctime.seconds = int(str_seconds)
		float_frames = float(str_frames)
		ctime.frames = int(float_frames * 75 / 100)
	except ArithmeticError:
		print('Bad time conversion')
	return ctime


def get_offset(line: str) -> str:
	match = regex.search(r'(\d{1,3}\.\d{1,7})', line)
	if match:
		return match.group(1)
	else:
		return ""


def get_color(line: str) -> str:
	match = regex.search(r'COLOR (.*?)$', line)
	if match:
		return match.group(1)
	else:
		return ""


def read_tracks(line_num, lines, track_list):
	numtracks = 0
	while line_num < len(lines):
		line = lines[line_num]  # should be TRACK NN AUDIO
		if "TRACK" in line:
			# print(line)
			newtrack = CueTrack()
			numtracks += 1
			newtrack.order = numtracks
			line_num += 1
			while line_num < len(lines):
				line = lines[line_num]
				if "TRACK" in line:
					break
				if "TITLE" in line:
					newtrack.title = get_quoted_string(line)
				if "INDEX" in line:
					# print(line)
					newtrack.index = get_cuetime(line)  # note this may be out in the hours component
					print(str(newtrack.order) + ": " + newtrack.title + ": " + str(newtrack.index.total_frames))
				if "OFFSET" in line:
					newtrack.offset = get_offset(line)
				if "COLOR" in line:
					newtrack.color = get_color(line)
				line_num += 1
			track_list.append(newtrack)


def determine_durations(tracks: list, total_duration: int):
	parent_track = CueTrack()
	for i in range(0, len(tracks) - 1):
		this_start = tracks[i].index.total_frames
		next_start = tracks[i + 1].index.total_frames
		tracks[i].duration_in_frames = next_start - this_start

		# we use red color to indicate tracks which are indented below a parent track
		if i > 0 and tracks[i].color == "red" and tracks[i - 1].color == "blue":  # this is the first indented item
			parent_track = tracks[i - 1]   # identify the parent track
		if i > 0 and tracks[i].color == "red":  # this is an indented item
			parent_track.duration_in_frames += tracks[i].duration_in_frames
	tracks[-1].duration_in_frames = total_duration - tracks[-1].index.total_frames


def read_header(header, line_num, lines):
	while line_num < len(lines):
		line = lines[line_num]
		if "TRACK" in line:
			break
		if "TITLE" in line:
			header.title = get_quoted_string(line)
		if "FILE" in line:
			fi, fo = get_file_and_format(line)
			path = os.path.split(header.cuefile)
			header.audiofile = os.path.join(path[0], fi)
			header.out_format = fo
			if file_is_ok(header.audiofile):
				duration = get_duration(header.audiofile)
				if duration > 0.0:
					header.duration_in_frames = int(75 * duration)
		if "PERFORMER" in line:
			header.performer = get_quoted_string(line)
		line_num += 1
	return line_num


def format_frames(frames: int, long_form: bool = False) -> str:
	ctime = CueTime(frames)
	chours = int(ctime.minutes / 60)
	ctime.minutes = ctime.minutes % 60
	if long_form:  # for Excel
		return str(chours).zfill(2) + "\t" + str(ctime.minutes).zfill(2) + "\t" + str(ctime.seconds).zfill(2)
	if chours > 0:
		return str(chours).zfill(2) + ':' + str(ctime.minutes).zfill(2) + ':' + str(ctime.seconds).zfill(2)
	else:
		return str(ctime.minutes).zfill(2) + ':' + str(ctime.seconds).zfill(2)


def index_title(atitle: str) -> str:
	# replace " by " in book titles
	atitle = atitle.replace(" by ", "~")
	pattern = "^(A|The) (.*?)~(.*?)$"
	match = regex.search(pattern, atitle)
	if match:
		atitle = match.group(2) + ", " + match.group(1) + "~" + match.group(3)
	return atitle


def get_track_before_time(tracks: list, time_in_secs: int) -> CueTrack:
	# work backwards to find heading immediately prior to current time, if not yet used
	track_num = len(tracks) - 1
	while track_num > 0:
		track: CueTrack = tracks[track_num]
		# print(f'{time_in_secs} : {track.title} : {track.index.total_seconds}')
		track_num -= 1
		if track.index.total_seconds <= time_in_secs:
			tracks.remove(track)
			return track
	return CueTrack()  # couldnt find it, so return an empty track


def process_cuefile(filename: str, passed_duration: int = 99999) -> Tuple[CueHeader, list]:
	header = CueHeader()
	header.cuefile = filename
	header.duration_in_frames = passed_duration  # we'll try to read this later from wave file
	track_list = []
	try:
		fileobject = open(filename, "r", encoding="utf-8")
	except IOError:
		print("Could not open " + filename)
		return header, track_list

	try:
		alltext = fileobject.read()
	except UnicodeDecodeError:
		print("Could not read " + filename)
		return header, track_list

	lines = alltext.splitlines(False)
	# read header lines, stop when we hit a track
	line_num = 0
	line_num = read_header(header, line_num, lines)

	if line_num >= len(lines):
		return header, track_list

	# if we get here, we're on first line of a track
	read_tracks(line_num, lines, track_list)
	if header.duration_in_frames == 0:  # if we didn't get a duration so far, estimate it
		last_track = track_list[-1]
		header.duration_in_frames = last_track.index.total_frames() + 1500  # estimate it as last track + 20 secs
	determine_durations(track_list, header.duration_in_frames)

	return header, track_list

def generate_output(header: CueHeader, tracks: list) -> str:
	accumulator = ""
	accumulator += 'TITLE "' + header.title + '"' + '\n'
	accumulator += 'FILE "' + header.file + '"' + ' ' + header.out_format + '\n'
	if header.performer:
		accumulator += 'PERFORMER "' + header.performer + '"' + '\n'
	track_count = 1
	for track in tracks:
		accumulator += '  TRACK ' + str(track_count).zfill(2) + ' AUDIO' + '\n'
		accumulator += '    TITLE "' + track.title + '"' + '\n'
		accumulator += '    INDEX 01 ' + str(track.index.minutes).zfill(2) + ':' + str(track.index.seconds).zfill(2) + ':' + str(track.index.frames).zfill(2) + '\n'
		if track.offset:
			accumulator += '    REM OFFSET ' + track.offset + '\n'
		accumulator += '    REM COLOR ' + track.color + '\n'
		track_count += 1
	return accumulator