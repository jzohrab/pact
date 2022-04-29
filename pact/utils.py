class TimeUtils:

    @staticmethod
    def time_string(ms):
        total_seconds = ms / 1000.0
        mins = int(total_seconds) // 60
        secs = total_seconds % 60
        return '{:02d}:{:04.1f}'.format(mins, secs)

    @staticmethod
    def interval_string(s, e, ifInvalid = 'n/a'):
        if (s >= e):
            return ifInvalid
        ss = TimeUtils.time_string(s)
        es = TimeUtils.time_string(e)
        return f'{ss} - {es}'
