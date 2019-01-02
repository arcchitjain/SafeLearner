base(coauthor(researcher, researcher)).
learn(coauthor/2).

base(author(researcher, paper)).
mode(author(+,-)).
mode(author(+,+)).

base(location(researcher, university)).
mode(location(+,-)).
mode(location(+,+)).

0.6::author(anton_dries, problog).
0.7::author(luc_de_raedt, problog).
0.9::author(angelika_kimmig, problog).
0.9::author(stefano_teso, coactive_learning).
0.8::author(mohit_kumar, coactive_learning).

0.9::location(jesse_davis, ku_leuven).
1::location(hendrik_blockeel, ku_leuven).
0.7::location(guy_van_den_broeck, ucla).
0.6::location(adnan_darwiche, ucla).

0.6::coauthor(adnan_darwiche,adnan_darwiche).
0.009::coauthor(adnan_darwiche,hendrik_blockeel).
0.009::coauthor(adnan_darwiche,jesse_davis).
0.903::coauthor(angelika_kimmig,angelika_kimmig).
0.54::coauthor(angelika_kimmig,anton_dries).
0.63::coauthor(angelika_kimmig,luc_de_raedt).
0.034::coauthor(angelika_kimmig,mohit_kumar).
0.036::coauthor(angelika_kimmig,stefano_teso).
0.613::coauthor(anton_dries,anton_dries).
0.42::coauthor(anton_dries,luc_de_raedt).
0.028::coauthor(anton_dries,mohit_kumar).
0.03::coauthor(anton_dries,stefano_teso).
0.18::coauthor(guy_van_den_broeck,guy_van_den_broeck).
0.011::coauthor(guy_van_den_broeck,hendrik_blockeel).
0.009::coauthor(guy_van_den_broeck,jesse_davis).
0.236::coauthor(hendrik_blockeel,hendrik_blockeel).
0.181::coauthor(hendrik_blockeel,jesse_davis).
0.217::coauthor(jesse_davis,jesse_davis).
0.71::coauthor(luc_de_raedt,luc_de_raedt).
0.03::coauthor(luc_de_raedt,mohit_kumar).
0.032::coauthor(luc_de_raedt,stefano_teso).
0.806::coauthor(mohit_kumar,mohit_kumar).
0.903::coauthor(stefano_teso,stefano_teso).
