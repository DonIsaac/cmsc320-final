from typing import List, Dict, TypedDict, Union

class StackOverflowQuestion(TypedDict):
    _id: int
    answer_count: int
    content_license: str
    creation_date: int
    is_answered: bool
    last_activity_date: int
    last_edit_date: int
    link: str
    question_id: int
    score: int
    tags: List[str]
    title: str
    view_count: int

class RawStackOverflowAnswer(TypedDict):
    """
    An answer scraped from a StackOverflow question.

    Each answer object contains the following keys:

    * `answer_id`   -- The ID of the answer (int). This is the same ID used
                        in the StackOverflow API, and is therefore unique to
                        the answer.

    * `snippets`    -- All code snippets contained in the answer, joined by
                        newlines.

    * `score`       -- The score of the answer (int). Upvotes minus downvotes.

    * `is_accepted` -- Whether the OP accepted the  answer is accepted (bool).

    * `source`      -- URL to the answer (str).

    * `author_id`   -- The User ID of the author (int | None). If answered 
                        anonymously, this will be None. If answered by
                        the community, this will be -1.

    * `author_name` -- The name of the author (str). May be `'anonymous'`
                        or `'community'`.

    * `page_pos`    -- The position of the answer on the page (int). Value
                        is [0, num_answers)

    * `is_highest_score` -- Whether the answer has the highest score among
                            all other answers (bool).

    * `question_has_highest_accepted_answer` -- Whether any of the answers
                                                to the question have the 
                                                highest score and are also
                                                accepted by the OP (bool).
    """

    # Unique answer ID
    answer_id: int

    # Author ID. May be -1 for some answers. When unable to scrape author ID,
    # this will be set to None
    author_id: Union[int, None]

    # Author's username. May be 'anonymous' or 'community'.
    author_username: str

    # OP has accepted answer as correct.
    is_accepted: bool

    # Whether this answer is the highest scored for the question.
    is_highest_scored: bool

    # The question has an answer that is both the accepted answer and has
    # more upvotes than any other answer.
    question_has_highest_accepted_answer: bool

    # Answer score. Upvotes minus downvotes. May be negative.
    score: int

    # 1-indexed position of answer on page relative to other answers.
    page_pos: int

    # All code snippets joined into a single string.
    snippets: str

    # URL to the answer.
    source: str
class StackOverflowAnswer(RawStackOverflowAnswer):
    """
    A StackOverflow answer as stored in the database.

    @see py:class::RawStackOverflowAnswer
    @see :py:class:`scrape.stack.RawStackOverflowAnswer`
    """

    # Unique answer ID. Same as `answer_id`
    _id: int

    # ID of the question the answer is for. This is a valid foreign key
    question_id: int