
import string
import cStringIO

class BaseCell(object):
    """ Base table cell """

    type = 'base'

    def __init__(self, row, col):
        self.row = row
        self.col = col

    def __repr__(self):
        return '{}({},{})'.format(self.__class__.__name__, self.row, self.col)


class EmptyCell(BaseCell):
    """ Default empty table cell """
    type = 'empty'


class Cell(BaseCell):
    """ A table cell filled with content spanning one
        or more rows or columns.
    """

    type = 'cell'

    def __init__(self, event, rowspan=1, colspan=1):
        self.event = event
        self.rowspan = rowspan
        self.colspan = colspan

    def __repr__(self):
        return '{}(rowspan={}, colspan={})'.format(self.__class__.__name__, self.rowspan, self.colspan)


class SpanCell(EmptyCell):
    """ A dummy cell used in combination with a Cell
        instance in order to represent the cells pre-allocated
        for rowspan/colspan > 1 of a Cell.
    """

    type = 'span'


def normalize(s):
    """ Normalize a string in order to be used as CSS class """
    s = s.lower().replace(u' ', u'-')
    s = u''.join([c for c in s if c in string.letters + string.digits])
    return s


class Table(object):
    """ Abstract HTML table model """

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.cells = []
        self.caption = None
        self.col_headers = list()
        self.row_headers = list()

        for row_index in range(0, rows):
            row = []
            for col_index in range(0, cols):
                row.append(EmptyCell(row_index, col_index))
            self.cells.append(row)

    def addCell(self, row, col, rowspan=1, colspan=1, event=None):

        # Check if the current cell is not actually in use
        if not isinstance(self.cells[row][col], EmptyCell):
            import pdb; pdb.set_trace() 
            raise ValueError('Cell [{}][{}] seems to be already in use'.format(row, col))

        # insert dummy span cells in case of a rowspan or colspan > 1
        for i in range(0, rowspan):
            for j in range(0, colspan):
                self.cells[row + i][col + j]  = SpanCell(row + i, col + j)
        # now insert content cell
        self.cells[row][col] = Cell(event, rowspan, colspan)

    def strip_trailing_rows(self):
        """ Remove trailing rows without attached events from
            end of the day.
        """

        rows = list()
        strip_mode = True
        for rownum, row in enumerate(reversed(self.cells)):
            len_row = len(row)
            num_empty = len([cell for cell in row if cell.type == 'empty'])
            if num_empty != len_row:
                strip_mode = False

            if num_empty == len_row and strip_mode:
                continue
            rows.append(row)

        self.cells = list(reversed(rows))

    def merge_cells(self):
        """ Merge vertical Cells representing the same event """

        for rownum, row in enumerate(self.cells):
            for colnum, cell in enumerate(row):
                if not isinstance(cell, Cell):
                    continue
                cols_to_merge = 0
                for i in range(colnum+1, len(row)):
                    if isinstance(self.cells[rownum][i], Cell) and self.cells[rownum][i].event == cell.event:
                        cols_to_merge += 1
                if cols_to_merge > 0:
                    cell.colspan = cols_to_merge + 1
                    for i in range(1, cols_to_merge + 1):
                        self.cells[rownum][colnum + i] = SpanCell(rownum, colnum + i)

    def render(self, event_renderer, merge_cells=True, strip_trailing_rows=True):
        """ Render the abstract table to HTML """

        if strip_trailing_rows:
            self.strip_trailing_rows()
        
        if merge_cells:
            self.merge_cells()


        out = list()
        out.append(u'<table class="schedule-table day-{}">'.format(self.weekday))

        # table caption
        if self.caption:
            out.append(u'<caption>{}</caption>'.format(self.caption))

        # column headers
        if self.col_headers:
            out.append(u'<thead>')
            out.append(u'<tr>')
            if self.row_headers:
                out.append(u'<th></th>')
            for hd in self.col_headers:
                out.append(u'<th>{}</th>'.format(hd))
#            if self.row_headers:
#                out.append(u'<th></th>')
            out.append(u'</tr>')
            out.append(u'</thead>')

        out.append('<tbody>')
        for row_index, row in enumerate(self.cells):
            out.append(u'<tr>')
            if self.row_headers:
                out.append(u'<th class="time">{}</th>'.format(self.row_headers[row_index]))
            for col, cell in enumerate(row):
                if isinstance(cell, SpanCell):
                    pass
                elif isinstance(cell, EmptyCell):
                    out.append(u'<td class="cell col-{} empty"></td>'.format(col))
                elif isinstance(cell, Cell):
                    out.append(u'<td class="cell title-{} col-{} non-empty" rowspan="{}" colspan="{}">{}</td>'.format(normalize(cell.event.title.text), col, cell.rowspan, cell.colspan, event_renderer(cell.event)))
#            if self.row_headers:
##                out.append(u'<th class="time">{}</th>'.format(self.row_headers[row_index]))

            out.append(u'</tr>')
        out.append('</tbody>')
        out.append(u'</table>')
        return u'\n'.join(out).encode('utf-8')


if __name__ == '__main__':

    rooms = [u'C01',
             u'B05/06',
             u'B07/08',
             u'B09',
             u'A08']

    hour_start = 7
    hour_end = 24
    resolution = 5

    row_headers = list()
    for hour in range(hour_start, hour_end + 1):
        for minute in range(0, 60, resolution):
            row_headers.append('{:02}:{:02}h'.format(hour, minute))
    table = Table(60/resolution * (hour_end - hour_start) , len(rooms))
    table.col_headers = rooms
    table.row_headers = row_headers
    table.addCell(1, 1, event='Meeting1')
    table.addCell(2, 1, event='Meeting2')
    table.addCell(2, 1, event='Meeting3')
    table.addCell(3, 2, rowspan=2, event='Long Meeting1')
    table.addCell(0, 2, colspan=2, event='Futter')

    def event_renderer(s):
        return '<div>{}</div>'.format(s)

    print table.render(event_renderer)
    
