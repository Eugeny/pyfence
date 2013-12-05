class RationalFormatter (object):
    def format(self, number):
        """
        Stringifies a number to numerator/denominator format
        Example::

            >>> print(RationalFormatter().format(1.25))
            5/4

        :param number: input number
        :type  number: float
        :raises      : None
        :rtype       : str
        """
        return '%i/%i' % number.as_integer_ratio()

    def display(self, number):
        print(str(number) + ' = ' + self.format(number))

