# reads a cue file and inserts chapters into the associated audio file

from mutagen.id3 import ID3, CTOC, CHAP, TIT2, TPE1, TALB, APIC, CTOCFlags
from mutagen.mp3 import MP3, error
import cuetools
import argparse
import pathlib

def main():
    parser = argparse.ArgumentParser(description='Process input arguments.')
    parser.add_argument('-i', '--input', help='Input .MP3 file')
    parser.add_argument('-c', '--cuefile', help='Cue .CUE file'),
    parser.add_argument('-p', '--picture', required=False, help='Image file (JPG or PNG)'),

    args = parser.parse_args()

    input_file = pathlib.Path(args.input)
    cue_file = pathlib.Path(args.cuefile)
    
    if cue_file.exists():
        header, tracks = cuetools.process_cuefile(cue_file)

    if input_file.exists():
        mp3_file = MP3(input_file, ID3=ID3)
        if not mp3_file.tags:
            mp3_file.add_tags()
        toc = CTOC(element_id=u"toc", flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED, child_element_ids=[], sub_frames=[TIT2(text=[u"TOC"])])
        mp3_file.tags.add(toc)
        title = header.title
        performer = header.performer
        mp3_file.tags["TIT2"] = TIT2(text=[title])
        mp3_file.tags["TALB"] = TALB(text=[title])
        mp3_file.tags["TPE1"] = TPE1(text=[performer])

        track: cuetools.CueTrack = None
        order = 0
        for track in tracks:
            order += 1
            duration = int(track.duration_in_frames * 1000/75)# convert to millisecs
            start_time = int(track.index.total_seconds * 1000) # convert to millisecs
            end_time = start_time + duration
            chapid = "chp" + str(order)
            # track_title = TIT2(text=[chapid])             
            track_title = TIT2(text=[track.title]) 
            chapter = CHAP(element_id=[chapid], flags=1, start_time=start_time, end_time=end_time, start_offset=0, end_offset=0, sub_frames=[track_title])
            # print(chapid,start_time,end_time,track_title)
            toc.child_element_ids.append(chapter.element_id)
            mp3_file.tags.add(chapter)

        if args.picture:
            picfile = args.picture
            if picfile.endswith('.jpg') or picfile.endswith('.jpeg'):
                mp3_file.tags.add(
                    APIC(encoding=3, mime='image/jpeg', type=2, desc= u'Cover',
                        data=open(picfile, 'rb').read())
                )
            else:
                if picfile.endswith('.png'):
                    mp3_file.tags.add(
                        APIC(encoding=3, mime='image/png', type=2, desc= u'Cover',
                            data=open(picfile, 'rb').read())
                    )

        mp3_file.save(input_file, v1=0, v2_version=4)

if __name__ == '__main__':
    main()
