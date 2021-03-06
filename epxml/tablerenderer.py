# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import shutil
import subprocess

import plac
import table
import util

from jinja2 import Environment, PackageLoader

env = Environment(loader=PackageLoader('epxml', 'templates'))


def normalize(s):
    """ Normalize a string in order to be used as CSS class """
    return s.lower().replace(u' ', u'-')


def event_renderer(event):
    """ Renders a single <event> as serialized
        through lxml.objectify as cell content for
        the schedule table.
    """
    result = list()

    try:
        css_outer = u' '.join(['topic-{}'.format(normalize(topic.topic.text)) for topic in event.topics])
    except AttributeError:
        css_outer = u''

    if event.category:
        css_outer += u' category-{}'.format(normalize(event.category.text))
    result.append(u'<div class="entry {}">'.format(css_outer))
#    result.append(u'<div class="time">{}</div>'.format(event.attrib['start-end']))
    result.append(u'<div class="title">{}</div>'.format(event.title))
    result.append(u'<div class="speakers">')
    if event.speakers.getchildren():
        for speaker in event.speakers:
            result.append(u'<div class="speaker">{}</div>'.format(speaker.speaker.name))
    result.append(u'</div>')
    result.append(u'</div>')
    return u''.join(result)


def conv(schedule_xml, # schedule XML string or schedule XML filename
        date_str,      # YYYY-MM-DD
        rooms,         # list of rooms
        hour_start=0,  # schedule starts
        hour_end=24,   # schedule ends
        resolution=15, # timeslot resolution in minutes
        caption=None,  # caption of table
        weekday=None,  # weekday name
        event_renderer=None):

    entries = util.get_entries(schedule_xml, '//day[@date="{}"]/entry'.format(date_str))

    row_headers = list()
    for hour in range(hour_start, hour_end + 1):
        for minute in range(0, 60, resolution):
            row_headers.append('{:02}:{:02}h'.format(hour, minute))
    tb = table.Table(60/resolution * (hour_end - hour_start) , len(rooms))
    tb.caption = caption
    tb.col_headers = rooms
    tb.row_headers = row_headers
    tb.weekday = weekday

    for e in entries:
        # determine starting row of event
        e_start = e.start.text      # format '0700'
        s_hour = int(e_start[:2])
        s_minute = int(e_start[2:])
        s_row = (s_hour - hour_start) * (60 / resolution) + s_minute / resolution

        # calculate row span over multiple time slots
        s_duration = int(e.duration)
        rowspan = s_duration / resolution 

        # determine col of event
        if e.room == 'ALL':
            # span over all columns
            s_col = 0
            colspan = len(rooms)
            tb.addCell(s_row, s_col, rowspan=rowspan, colspan=colspan, event=e)
        else:
            for room in e.room.text.split(','):
                if room in rooms:
                    s_col = rooms.index(room)
                    colspan = 1
                    tb.addCell(s_row, s_col, rowspan=rowspan, colspan=colspan, event=e)

    return tb.render(event_renderer=event_renderer)


@plac.annotations(
    xml_in=('Schedule XML file', 'option', 'i'),
    html_out=('Output HTML file', 'option', 'o'),
    template=('Rendering template', 'option', 't'),
    first_page_number=('Start with page number XX', 'option', 'n'),
    pdf_filename=('Custom PDF output filename', 'option', 'f'),
    fontpath=('Directory containing fonts', 'option', 'y')
    )
def render_schedule(xml_in, html_out='table.html', template='brochure_schedule.pt', fontpath=None, pdf_filename=None, first_page_number=1):

    rooms = [u'C01', u'B05/B06', u'B07/B08', u' ',  u'B09', u'A08', 'A03/A04', 'A05/A06']

    if not xml_in:
        raise ValueError('Missing --xml-in|-i parameter')
    with open(xml_in, 'rb') as fp:
        schedule_xml = fp.read()

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    days_html = []
    for count, i in enumerate(range(21, 28)):
        html = conv(schedule_xml,
                   '2014-07-{}'.format(i),
                   rooms,
                   hour_start=9,
                   hour_end=22,
                   resolution=15,
#                   caption=u'2014-07-{}'.format(i),
                   caption=days[count],
                   weekday=days[count],
                   event_renderer=event_renderer
                   )
        days_html.append(unicode(html, 'utf8'))

    template = env.get_template(template)
    html = template.render(
            days=days_html,
            first_page_number=int(first_page_number) - 2,
            second_page_number=int(first_page_number) - 1,
            view=util.JinjaView())

    with open(html_out, 'wb') as fp:
        fp.write(html.encode('utf8'))
        print 'HTML output written to {}'.format(html_out)

    # write HTML file to a dedicated scratch directory
    tmpd = tempfile.mkdtemp()
    html_filename  = os.path.join(tmpd, 'index.html')
    with open(html_filename, 'wb') as fp:
        fp.write(html.encode('utf-8'))

    # copy over conversion resources
    resources_dir = os.path.join(os.path.dirname(__file__), 'templates', 'resources')
    for dirname, dirnames, filenames in os.walk(resources_dir):
        for fname in filenames:
            shutil.copy(os.path.join(dirname, fname), tmpd)

    if fontpath and os.path.exists(fontpath):
        for filename in os.listdir(fontpath):
            shutil.copy(os.path.join(fontpath, filename), tmpd)

    if pdf_filename:
        out_pdf = pdf_filename
    else:
        out_pdf = '{}.pdf'.format(os.path.splitext(html_filename)[0])
    cmd = '/opt/PDFreactor7/bin/pdfreactor "{}" "{}"'.format(html_filename, out_pdf)
    print 'Running: {}'.format(cmd)
    proc = subprocess.Popen(cmd, shell=True)
    status = proc.wait()
    print 'Exit code: {}'.format(status)
    if status != 0:
        raise RuntimeError('PDF generation failed')
    print 'PDF written to "{}"'.format(out_pdf)
    return out_pdf


def main():
    plac.call(render_schedule)


if __name__ == '__main__':
    main()
