
from problog.engine import DefaultEngine
from problog.logic import Term
from problog import get_evaluatable


class DataFile(object):
    """Represents a data file. This is a wrapper around a ProbLog file that offers direct
    querying and evaluation functionality.

    :param source: ProbLog logic program
    :type source: LogicProgram
    """

    def __init__(self, *sources):
        self._database = DefaultEngine().prepare(sources[0])
        self._source_files = sources[0].source_files
        for source in sources[1:]:
            for clause in source:
                self._database += clause

    def query(self, functor, arity=None, arguments=None):
        """Perform a query on the data.
        Either arity or arguments have to be provided.

        :param functor: functor of the query
        :param arity: number of arguments
        :type arity: int | None
        :param arguments: arguments
        :type arguments: list[Term]
        :return: list of argument tuples
        :rtype: list[tuple[Term]]
        """
        if arguments is None:
            assert arity is not None
            arguments = [None] * arity

        query = Term(functor, *arguments)
        return self._database.engine.query(self._database, query)

