---
slug: is-this-a-good-unit-test
title: Is this a good unit test?
author: Jonathon Waterhouse
summary: 
created_at: 2021-04-05
---

I came across some unit tests at work the other dayyyyyy. They were checking that various queries built using the SQLAlchemy session query builder were generating the appropriate SQL query strings. A contrived example is below:

```python
from db.models import User

def test_query(session):
    query = session.query(User).filter(email="test@example.com")

    assert query.sql == "SELECT user.id, user.name, user.email WHERE user.email = 'test@example.com'"
```

A couple of things to note about this query:

- `sqlalchemy.orm.Query` has been extended to include the `.sql` property you can see used in the `assert` line - this is just a convenience function to run `self.statement.compile(compile_kwargs={"literal_binds": True})` which is commonly used to debug the query builder.
- the `.sql` property is used in production code to send a query to the database.
- this really is a contrived example, the actual unit tests were testing much more complicated queries that drew on third-party extensions.

Now, hopefully your spidey-sense tingled about the use of compiling the query using `literal_binds` before sending it to the database - this is potentially vulnerable to an SQL-injection attack (which SQLAlchemy themselves are [very clear about](https://docs.sqlalchemy.org/en/14/faq/sqlexpressions.html#rendering-bound-parameters-inline))! In this particular case there was very low risk of that happening, but we rectified it anyway to use the proper query with bound parameters. But even with that fixed, is this still a good unit test?

I'm genuinely not sure. Some things I don't think are good about it:

- if `.sql` is not used in production code anyway, then this test is no longer testing a production code path. It's really just testing SQLAlchemy's (and extensions) query renderer. Is that helpful?
- it doesn't tell you if the effect of the query (e.g. the data returned, or the table updated) is what you expect, which is probably more useful.

But there are some things I think are useful about it too:

- for complex queries, checking that the query string looks like you'd expect might still be useful.
- it's very readable.
- paired with integration tests that do actually test the query executes as expected, this kind of test is nicely complementary.

In summary I suppose that on its own this isn't a very useful test, but paired with an integration test it's good?

Addendum - since I'm going on about it, here's some other random thoughts on tests in no particular order:

- A co-worker has the belief that unit tests form the primary documentation for a function, outside of the function code itself. That is, to know how a reasonably complex function works you should consult its tests. I disagree with this primarily on developer experience grounds - I'd hate to have to read the tests of each function to be confident on how to use it. (This co-worker was also not a fan of docstrings or commenting in general, which I also disagree with.)
- Chasing a too-high (say >80%?) code coverage score is not worth the effort. The tests often end up being low quality when the goal becomes chasing a number rather than actually checking code.
- Most tests should look something like `assert foo(input) == expected` for a series of `input`/`expected` pairs. The inner workings of the function need not be tested (unless it's particularly important). I've seen a lot of tests that check each line of a function calls the expected method, with the expected arguments, etc. Not only does it make tests long and complex but usually this is just testing something that has already been tested elsewhere.
- Clean, readable, sanely-commented code > unit tests, but there's really no reason not to do both.
