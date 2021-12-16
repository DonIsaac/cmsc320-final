from typing import List, Dict, TypedDict, Union, Any

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

def is_stackoverflow_question(q: Any) -> bool:
    if q is None or not isinstance(q, dict):
        return False

    if '_id' not in q or \
       'answer_count' not in q or \
       'content_license' not in q or \
       'creation_date' not in q or \
       'is_answered' not in q or \
       'last_activity_date' not in q or \
       'last_edit_date' not in q or \
       'link' not in q or \
       'question_id' not in q or \
       'score' not in q or \
       'tags' not in q or \
       'title' not in q or \
       'view_count' not in q:
        return False

    if not isinstance(q['_id'], int) or \
       not isinstance(q['answer_count'], int) or \
       not isinstance(q['content_license'], str) or \
       not isinstance(q['creation_date'], int) or \
       not isinstance(q['is_answered'], bool) or \
       not isinstance(q['last_activity_date'], int) or \
       not isinstance(q['last_edit_date'], int) or \
       not isinstance(q['link'], str) or \
       not isinstance(q['question_id'], int) or \
       not isinstance(q['score'], int) or \
       not isinstance(q['tags'], list) or \
       not isinstance(q['title'], str) or \
       not isinstance(q['view_count'], int):
        return False

    return True

def is_raw_stackoverflow_answer(a: Any) -> bool:
    if a is None or not isinstance(a, dict):
        return False

    if 'answer_id' not in a or \
       'author_id' not in a or \
       'author_username' not in a or \
       'is_accepted' not in a or \
       'is_highest_scored' not in a or \
       'question_has_highest_accepted_answer' not in a or \
       'page_pos' not in a or \
       'score' not in a or \
       'snippets' not in a or \
       'source' not in a:
        return False

    if not isinstance(a['answer_id'], int) or \
       not (a['author_id'] is None or isinstance(a['author_id'], int)) or \
       not isinstance(a['author_username'], str) or \
       not isinstance(a['is_accepted'], bool) or \
       not isinstance(a['is_highest_scored'], bool) or \
       not isinstance(a['question_has_highest_accepted_answer'], bool) or \
       not isinstance(a['page_pos'], int) or \
       not isinstance(a['score'], int) or \
       not isinstance(a['snippets'], str) or \
       not isinstance(a['source'], str):
        return False

    return True

def is_stackoverflow_answer(a: Any) -> bool:
    return is_raw_stackoverflow_answer(a) and \
        '_id' in a and \
        isinstance(a['_id'], int) and \
        'question_id' in a and \
        isinstance(a['question_id'], int)
