from math import pi


class Filter:
    def __call__(self, value: float, dt: float) -> float:
        return self.filter(value, dt)

    def filter(self, value: float, dt: float) -> float:
        raise NotImplementedError()


class _SingleCutoffFreqFilter(Filter):
    def __init__(self, cutoff_freq: float, init_value: float = 0.0):
        self._cutoff_freq = None
        self.set_cutoff_freq(cutoff_freq)

        self._prev_output = init_value

    def get_cutoff_freq(self) -> float:
        return self._cutoff_freq

    def set_cutoff_freq(self, cutoff_freq: float) -> None:
        self._check_cutoff_freq(cutoff_freq)
        self._cutoff_freq = cutoff_freq

    def _check_cutoff_freq(self, cutoff_freq: float) -> None:
        if cutoff_freq < 0:
            raise ValueError(f'cutoff_freq must be >= 0; got {cutoff_freq}.')

    def filter(self, value: float, dt: float) -> float:
        output = self._filter(value, dt)
        self._prev_output = output
        return output

    def _filter(self, value: float, dt: float) -> float:
        raise NotImplementedError()


class LowPassFilter(_SingleCutoffFreqFilter):
    """
    Passes signals lower than the cutoff frequency. Decreases signals higher
    than the cutoff frequency. The higher a signal's frequency is above the
    cutoff frequency, the more the signal is decreased.

    Frequency response::

        gain
        1|-------\\
         |       .\\
         |       . \\
        0|_______.__\\_______ freq
                 ^cutoff_freq

    This is also known as a "moving average".

    This is useful for example if you have a sensor reading that is really
    "noisy" (perhaps an accelerometer or distance sensor), and you want to get a
    sort of averaged, slower-moving reading from the noisy readings.

    https://en.wikipedia.org/wiki/Low-pass_filter
    """

    def _filter(self, value: float, dt: float) -> float:
        alpha = self._get_alpha(dt)
        return alpha * value + (1 - alpha) * self._prev_output

    def _get_alpha(self, dt: float) -> float:
        cutoff_freq = self.get_cutoff_freq()
        a = 2 * pi * dt * cutoff_freq
        return a / (a + 1)


class HighPassFilter(_SingleCutoffFreqFilter):
    """
    Passes signals higher than the cutoff frequency. Decreases signals lower
    than the cutoff frequency. The lower a signal's frequency is below the
    cutoff frequency, the more the signal is decreased.

    Frequency response::

        gain
        1|          /-------
         |         /.
         |        / .
        0|_______/__._______ freq
                    ^cutoff_freq

    This is useful for example if you have a sensor reading that has a slowly
    changing bias, for example a gyroscope. This can remove the bias from the
    rapidly varying true signal.

    https://en.wikipedia.org/wiki/High-pass_filter
    """

    def __init__(self, cutoff_freq: float, init_value: float = 0.0):
        super().__init__(cutoff_freq, init_value)
        self._prev_value = init_value

    def _filter(self, value: float, dt: float) -> float:
        d_value = value - self._prev_value
        self._prev_value = value

        alpha = self._get_alpha(dt)
        return alpha * (self._prev_output + d_value)

    def _get_alpha(self, dt: float) -> float:
        cutoff_freq = self.get_cutoff_freq()
        return 1 / (2 * pi * dt * cutoff_freq + 1)


class _LowHighCutoffFreqsFilter(Filter):
    def __init__(
            self,
            low_cutoff_freq: float,
            high_cutoff_freq: float
    ):
        self._check_cutoff_freqs(low_cutoff_freq, high_cutoff_freq)

    def _check_cutoff_freqs(
            self,
            low_cutoff_freq: float,
            high_cutoff_freq: float
    ) -> None:
        if low_cutoff_freq > high_cutoff_freq:
            raise ValueError(
                f'low_cutoff_freq ({low_cutoff_freq}) cannot be higher than '
                f'high_cutoff_freq ({high_cutoff_freq}).'
            )

    def set_cutoff_freqs(
            self,
            low_cutoff_freq: float,
            high_cutoff_freq: float
    ) -> None:
        self._check_cutoff_freqs(low_cutoff_freq, high_cutoff_freq)


class BandPassFilter(_LowHighCutoffFreqsFilter):
    """
    Passes signals between the cutoff frequencies. Decreases signals outside
    the cutoff frequencies. The further a signal's frequency is outside the
    cutoff frequency band, the more the signal is decreased.

    Frequency response::

        gain
        1|             /-------\\
         |            /.       .\\
         |           / .       . \\
        0|__________/__._______.__\\________ freq
        low_cutoff_freq^       ^high_cutoff_freq

    https://en.wikipedia.org/wiki/Band-pass_filter
    """

    def __init__(
            self,
            low_cutoff_freq: float,
            high_cutoff_freq: float,
            init_value: float = 0.0
    ):
        super().__init__(low_cutoff_freq, high_cutoff_freq)

        self._hpf = HighPassFilter(low_cutoff_freq, init_value=init_value)
        self._lpf = LowPassFilter(high_cutoff_freq, init_value=init_value)

    def set_cutoff_freqs(
            self,
            low_cutoff_freq: float,
            high_cutoff_freq: float
    ) -> None:
        super().set_cutoff_freqs(low_cutoff_freq, high_cutoff_freq)

        self._hpf.set_cutoff_freq(low_cutoff_freq)
        self._lpf.set_cutoff_freq(high_cutoff_freq)

    def filter(self, value: float, dt: float) -> float:
        value = self._hpf(value, dt)
        value = self._lpf(value, dt)
        return value


class BandStopFilter(_LowHighCutoffFreqsFilter):
    """
    Passes signals outside the cutoff frequencies. Decreases signals inside
    the cutoff frequencies. The further a signal's frequency is inside the
    cutoff frequency band, the more the signal is decreased.

    Frequency response::

        gain
        1|-------------\\             /----------
         |             .\\           /.
         |             . \\         / .
        0|_____________.__\\_______/__.___________ freq
        low_cutoff_freq^             ^high_cutoff_freq

    https://en.wikipedia.org/wiki/Band-stop_filter
    """

    def __init__(
            self,
            low_cutoff_freq: float,
            high_cutoff_freq: float,
            init_value: float = 0.0
    ):
        super().__init__(low_cutoff_freq, high_cutoff_freq)

        self._lpf = LowPassFilter(low_cutoff_freq, init_value=init_value)
        self._hpf = HighPassFilter(high_cutoff_freq, init_value=init_value)

    def set_cutoff_freqs(
            self,
            low_cutoff_freq: float,
            high_cutoff_freq: float
    ) -> None:
        super().set_cutoff_freqs(low_cutoff_freq, high_cutoff_freq)

        self._lpf.set_cutoff_freq(low_cutoff_freq)
        self._hpf.set_cutoff_freq(high_cutoff_freq)

    def filter(self, value: float, dt: float) -> float:
        return self._lpf(value, dt) + self._hpf(value, dt)
