base(coauthor(researcher, researcher)).
learn(coauthor/2).

base(author(researcher, paper)).
mode(author(+,-)).
mode(author(+,+)).

base(location(researcher, university)).
mode(location(+,-)).
mode(location(+,+)).

0.9::author(bob, plp).
0.6::author(carl, plp).
0.7::author(greg, plp).
0.9::author(ian, db).
0.8::author(harry, db).

1::location(edwin, harvard).
0.9::location(fred, harvard).
0.6::location(alice, mit).
0.7::location(dave, mit).

0.2::coauthor(alice, edwin).
0.3::coauthor(alice, fred).
0.4::coauthor(bob, carl).
0.5::coauthor(bob, greg).
0.6::coauthor(bob, harry).
0.7::coauthor(bob, ian).
0.8::coauthor(carl, greg).
0.9::coauthor(carl, harry).
0.8::coauthor(carl, ian).
0.7::coauthor(dave, edwin).
0.6::coauthor(dave, fred).
0.5::coauthor(edwin, fred).
0.4::coauthor(greg, harry).
0.3::coauthor(greg, ian).
0.2::coauthor(ian, ian).