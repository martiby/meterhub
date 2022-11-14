import json
from bottle import route, response

class Trace:
    """
    Trace for MeterHub

    The individual measurements are saved in a list. The length can be changed at runtime.
    The trace buffer is available as CSV or JSON via the web server.

    /trace/<SIZE>
    /trace/csv
    /trace/json
    """

    def __init__(self, size=0):
        self.size = None
        self.set_size(size)
        self.data = []
        print("init")

    def push(self, data):
        """
        Push dataset to trace buffer
        """
        if data and self.size > 0:
            self.data.append(data)
            self.data = self.data[-self.size:]  # limit to maximum length

    def set_size(self, size):
        """
        Set size (number) of stored trace datasets
        """
        if isinstance(size, int) and size >= 0:
            self.size = size
        return self.size

    def get_csv(self, columns=None):
        """
        Get trace data as CSV
        """
        try:
            if columns is None:  # retrive columns from first dataset
                columns = list(sorted(self.data[0].keys()))
                # set 'time' and 'timestamp' to the left for sorted colums
                if 'timestamp' in columns:
                    columns.remove('timestamp')
                    columns = ['timestamp'] + columns
                if 'time' in columns:
                    columns.remove('time')
                    columns = ['time'] + columns

            csv = ";".join(columns) + '\n'
            for d in self.data:
                csv += ";".join(["{}".format(d[c]) for c in columns]) + '\n'
        except:
            csv = ''
        return csv


trace = Trace(size=600)


@route("/trace")
@route("/trace/<size>")
def trace_set(size=None):
    return "trace.size={}".format(trace.set_size(size))


@route("/trace/json")
def trace_json():
    response.content_type = 'application/json'
    return json.dumps(trace.data)


@route("/trace/csv")
def trace_csv():
    response.content_type = 'text/plain'
    return trace.get_csv()


if __name__ == "__main__":
    trace.push({'a': 1, 'b': 2})
    trace.push({'a': 10, 'b': 20})
    print(trace.get_csv(columns=('a', 'b')))
