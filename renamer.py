#!/usr/bin/python

import re
import sys
import glob
import urllib
import shutil
import os.path
import optparse
import xml.dom.minidom

apikey='43B3C09FB8CACD87'
apihost='www.thetvdb.com'
apiport='80'
apipath='api'

class TVDB:
	def get_series(self, show_name):
		series_list=[]

		searchpath="GetSeries.php"
		searchstring=urllib.urlencode({'seriesname': show_name})
		url="http://%s:%s/%s/%s?%s" % (apihost, apiport, apipath, searchpath, searchstring)

		if(options.verbose):
			print "Fetching", url

		search_xml=urllib.urlopen(url);
		search_dom=xml.dom.minidom.parse(search_xml)
		datablock=search_dom.firstChild;

		if (datablock.nodeName == 'Error'):
			raise Exception("TVDB Error: %s" % (datablock.firstChild.data))
		elif (datablock.nodeName != 'Data'):
			raise Exception("Parser error: unknown response container.  XML follows.\n%s" % datablock.toxml())

		series_nodes=search_dom.getElementsByTagName('Series')

		for series_node in series_nodes:
			series_id=series_node.getElementsByTagName('seriesid')[0].firstChild.data
			series_name=series_node.getElementsByTagName('SeriesName')[0].firstChild.data

			series=Series()
			series.series_id=series_id
			series.name=series_name

			series_list.append(series)

		return series_list

	def get_episodes(self, series_id):
		episodes=[]

		searchpath="%s/series/%s/all/en.xml" % (apikey, series_id)
		url="http://%s:%s/%s/%s" % (apihost, apiport, apipath, searchpath)
		if(options.verbose):
			print "Fetching", url

		search_xml=urllib.urlopen(url)
		search_dom=xml.dom.minidom.parse(search_xml)
		episode_nodes=search_dom.getElementsByTagName('Episode');

		for episode_node in episode_nodes:
			episode=Episode()

			airdate=episode_node.getElementsByTagName('FirstAired')[0]
			if(airdate.firstChild):
				episode.airdate=airdate.firstChild.data

			episode.season_number=int(episode_node.getElementsByTagName('SeasonNumber')[0].firstChild.data)
			episode.number=int(episode_node.getElementsByTagName('EpisodeNumber')[0].firstChild.data)
			episode.title=episode_node.getElementsByTagName('EpisodeName')[0].firstChild.data

			episodes.append(episode)

		return episodes


class Series:
	def __init__(self):
		self.name=None
		self.series_id=None
		self.episodes=[]

	def load_episodes(self):
		if(not self.series_id):
			raise Exception("Cannot search for episodes without a series_id.");

		tvdb=TVDB()
		self.episodes=tvdb.get_episodes(self.series_id)

	def get_episode_for_date(self, date):
		for episode in self.episodes:
			if (episode.airdate == date):
				return episode

		return False


class Episode:
	def __init__(self):
		self.title=None
		self.number=None
		self.airdate=None
		self.season_number=None



def parse_args(): 
	parser=optparse.OptionParser()
	parser.add_option("-D", dest="delete", action="store_true", help="Delete source directory after moving")
	parser.add_option("-v", dest="verbose",  action="store_true", help="Run verbosely")
	parser.add_option("-d", dest="videopath", help="Path to save renamed file to")

	(options,args)=parser.parse_args()

	if(options.delete and not options.videopath):
		print >> sys.stderr, "You cannot delete (-D) without a target path (-d)."
		sys.exit(1)

	if(not args):
		print >> sys.stderr, "You must specify a file name."
		sys.exit(1)

	return (options, args)

def get_series(showname):
	tvdb=TVDB()
	series_matches=tvdb.get_series(showname)

	if(len(series_matches) < 1):
		print >> sys.stderr, "No series found for '%s'.  Try a different search." % (showname)
		sys.exit(1)

	if(len(series_matches) > 1 and options.verbose):
		print "Multiple series found.  Using top match."

	series=series_matches[0]

	return series

def process(source):
	source_path=os.path.dirname(source)
	source_filename=os.path.basename(source)
	source_nameparts=os.path.splitext(source_filename)
	source_basename=source_nameparts[0]
	source_extension=source_nameparts[1]

	nameparser=re.compile('(.*?)[- _\.](\d\d\d\d[- /_\.]\d\d[- /_\.]\d\d)[- /_\.]?(.*)')
	match=nameparser.match(source_basename);

	if(match):
		(raw_showname, raw_showdate, rest)=match.group(1, 2, 3)
		parsed_showname=re.sub('[\._-]', ' ', raw_showname)
		parsed_showdate=re.sub('[/\._ ]', '-', raw_showdate)
	else:
		print >> sys.stderr, "Could not parse name component:",  source_basename
		sys.exit(1)

	if(options.verbose):
		print "Name:", parsed_showname
		print "Date:", parsed_showdate

	series=get_series(parsed_showname)

	if(options.verbose):
		print "Loading episodes.  This may take a moment."

	series.load_episodes()

	if(len(series.episodes)<1):
		print >> sys.stderr, "No episodes found for '%s'." % (series.name)
		sys.exit(1)

	episode=series.get_episode_for_date(parsed_showdate)

	if(not episode):
		print >> sys.stderr, "No episode of '%s' found for airdate '%s'." % (series.name, parsed_showdate)
		sys.exit(1)


	target_filename="%s - %dx%02d (%s) - %s%s" % (series.name, 
						      episode.season_number, 
						      episode.number, 
						      episode.airdate, 
						      episode.title,
						      source_extension)

	if(options.videopath != None):
		target_path="%s/%s" % (options.videopath, series.name)
	else:
		target_path=source_path;
		if(target_path == ''):
			target_path='.'

	if(options.verbose):
		print "Old Name:", source_filename
		print "New Name:", target_filename
		print "Target path:", target_path

	if (not os.path.exists(target_path)):
		try:
			if(options.verbose):
				print "Making", target_path
			os.makedirs(target_path)
		except:
			print "Could not make destination path", target_path
			sys.exit(1)


	try:
		shutil.move(source, "%s/%s" % (target_path, target_filename))
	except:
		print "Failed to move show to %s.  Exiting." % (target_path)
		sys.exit(1)
	
	if(options.delete):
		if(options.verbose):
			print "Deleting", source_path
		shutil.rmtree(source_path)

### MAIN ###
(options,args)=parse_args()

provided_path=args[0]

if(os.path.isdir(provided_path)):
	for extension in ('avi', 'mkv', 'mpeg', 'ts'):
		filelist=glob.glob("%s/*.%s" % (provided_path, extension))
		for file in filelist:
			process(file)
else:
	process(provided_path)

print "Succeeded!";

sys.exit(0)
