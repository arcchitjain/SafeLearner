base(all100(object, object)).
base(some100(object, object)).
base(no100(object, object)).
base(somenot100(object, object)).
base(rall100(object, object)).
base(rsome100(object, object)).
base(rno100(object, object)).
base(rsomenot100(object, object)).
base(rnvc100(object, object)).
mode(all100(+, +)).
mode(all100(+, -)).
mode(all100(-, +)).
mode(some100(+, +)).
mode(some100(+, -)).
mode(some100(-, +)).
mode(no100(+, +)).
mode(no100(+, -)).
mode(no100(-, +)).
mode(somenot100(+, +)).
mode(somenot100(+, -)).
mode(somenot100(-, +)).

all100(a1, b1).
all100(b1, c1).
all100(b2, a2).
some100(c2, b2).
some100(b3, a3).
all100(b3, c3).
no100(a4, b4).
all100(c4, b4).
somenot100(b5, a5).
no100(c5, b5).
all100(a6, b6).
somenot100(b6, c6).
no100(b7, a7).
somenot100(c7, b7).
somenot100(b8, a8).
some100(b8, c8).
no100(b9, a9).
some100(b9, c9).
some100(a10, b10).
no100(c10, b10).
some100(b11, a11).
some100(c11, b11).
no100(a12, b12).
no100(c12, b12).
some100(a13, b13).
somenot100(c13, b13).
no100(b14, a14).
somenot100(b14, c14).
somenot100(b15, a15).
somenot100(b15, c15).
some100(b16, a16).
somenot100(c16, b16).
somenot100(a17, b17).
somenot100(c17, b17).
no100(b18, a18).
all100(c18, b18).
somenot100(a19, b19).
no100(b19, c19).
somenot100(b20, a20).
some100(c20, b20).
no100(a21, b21).
somenot100(b21, c21).
no100(b22, a22).
no100(c22, b22).
some100(a23, b23).
some100(c23, b23).
all100(b24, a24).
somenot100(c24, b24).
somenot100(a25, b25).
no100(c25, b25).
all100(a26, b26).
some100(b26, c26).
somenot100(a28, b28).
somenot100(b28, c28).
all100(b29, a29).
somenot100(b29, c29).
some100(b30, a30).
no100(b30, c30).
no100(b31, a31).
all100(b31, c31).
all100(a32, b32).
somenot100(c32, b32).
all100(b34, a34).
all100(c34, b34).
all100(b35, a35).
some100(b35, c35).
all100(a36, b36).
no100(b36, c36).
all100(b37, a37).
no100(c37, b37).
somenot100(a38, b38).
some100(b38, c38).
some100(a39, b39).
all100(c39, b39).
no100(a40, b40).
some100(b40, c40).
somenot100(a41, b41).
some100(c41, b41).
no100(a42, b42).
some100(c42, b42).
some100(a43, b43).
some100(b43, c43).
somenot100(b44, a44).
all100(c44, b44).
all100(b45, a45).
all100(b45, c45).
all100(a46, b46).
some100(c46, b46).
some100(a47, b47).
somenot100(b47, c47).
some100(b48, a48).
somenot100(b48, c48).
no100(a49, b49).
somenot100(c49, b49).
all100(a50, b50).
no100(c50, b50).
some100(a51, b51).
all100(b51, c51).
some100(b54, a54).
some100(b54, c54).
no100(a55, b55).
all100(b55, c55).
some100(b56, a56).
no100(c56, b56).
somenot100(b57, a57).
all100(b57, c57).
no100(b58, a58).
no100(b58, c58).
somenot100(a59, b59).
all100(c59, b59).
some100(b60, a60).
all100(c60, b60).
somenot100(a61, b61).
all100(b61, c61).
no100(a62, b62).
no100(b62, c62).
some100(a63, b63).
no100(b63, c63).
rall100(a1, c1).
0::rall100(c1,a1).
0::rsome100(a1,c1).
0::rsome100(c1,a1).
0::rno100(a1,c1).
0::rno100(c1,a1).
0::rsomenot100(a1,c1).
0::rsomenot100(c1,a1).
0::rnvc100(a1,c1).
rsomenot100(c2, a2).
0::rall100(a2,c2).
0::rall100(c2,a2).
0::rsome100(a2,c2).
0::rsome100(c2,a2).
0::rno100(a2,c2).
0::rno100(c2,a2).
0::rsomenot100(a2,c2).
0::rnvc100(a2,c2).
rsome100(a3, c3).
0::rall100(a3,c3).
0::rall100(c3,a3).
0::rsome100(c3,a3).
0::rno100(a3,c3).
0::rno100(c3,a3).
0::rsomenot100(a3,c3).
0::rsomenot100(c3,a3).
0::rnvc100(a3,c3).
rsome100(c4, a4).
0::rall100(a4,c4).
0::rall100(c4,a4).
0::rsome100(a4,c4).
0::rno100(a4,c4).
0::rno100(c4,a4).
0::rsomenot100(a4,c4).
0::rsomenot100(c4,a4).
0::rnvc100(a4,c4).
rsomenot100(a5, c5).
0::rall100(a5,c5).
0::rall100(c5,a5).
0::rsome100(a5,c5).
0::rsome100(c5,a5).
0::rno100(a5,c5).
0::rno100(c5,a5).
0::rsomenot100(c5,a5).
0::rnvc100(a5,c5).
rsomenot100(c6, a6).
0::rall100(a6,c6).
0::rall100(c6,a6).
0::rsome100(a6,c6).
0::rsome100(c6,a6).
0::rno100(a6,c6).
0::rno100(c6,a6).
0::rsomenot100(a6,c6).
0::rnvc100(a6,c6).
rall100(c7, a7).
0::rall100(a7,c7).
0::rsome100(a7,c7).
0::rsome100(c7,a7).
0::rno100(a7,c7).
0::rno100(c7,a7).
0::rsomenot100(a7,c7).
0::rsomenot100(c7,a7).
0::rnvc100(a7,c7).
rsome100(a8, c8).
0::rall100(a8,c8).
0::rall100(c8,a8).
0::rsome100(c8,a8).
0::rno100(a8,c8).
0::rno100(c8,a8).
0::rsomenot100(a8,c8).
0::rsomenot100(c8,a8).
0::rnvc100(a8,c8).
rall100(c9, a9).
0::rall100(a9,c9).
0::rsome100(a9,c9).
0::rsome100(c9,a9).
0::rno100(a9,c9).
0::rno100(c9,a9).
0::rsomenot100(a9,c9).
0::rsomenot100(c9,a9).
0::rnvc100(a9,c9).
rsomenot100(c10, a10).
0::rall100(a10,c10).
0::rall100(c10,a10).
0::rsome100(a10,c10).
0::rsome100(c10,a10).
0::rno100(a10,c10).
0::rno100(c10,a10).
0::rsomenot100(a10,c10).
0::rnvc100(a10,c10).
rsome100(a11, c11).
0::rall100(a11,c11).
0::rall100(c11,a11).
0::rsome100(c11,a11).
0::rno100(a11,c11).
0::rno100(c11,a11).
0::rsomenot100(a11,c11).
0::rsomenot100(c11,a11).
0::rnvc100(a11,c11).
rsome100(c12, a12).
0::rall100(a12,c12).
0::rall100(c12,a12).
0::rsome100(a12,c12).
0::rno100(a12,c12).
0::rno100(c12,a12).
0::rsomenot100(a12,c12).
0::rsomenot100(c12,a12).
0::rnvc100(a12,c12).
rsome100(c13, a13).
0::rall100(a13,c13).
0::rall100(c13,a13).
0::rsome100(a13,c13).
0::rno100(a13,c13).
0::rno100(c13,a13).
0::rsomenot100(a13,c13).
0::rsomenot100(c13,a13).
0::rnvc100(a13,c13).
rsomenot100(c14, a14).
0::rall100(a14,c14).
0::rall100(c14,a14).
0::rsome100(a14,c14).
0::rsome100(c14,a14).
0::rno100(a14,c14).
0::rno100(c14,a14).
0::rsomenot100(a14,c14).
0::rnvc100(a14,c14).
rnvc100(a15, c15).
0::rall100(a15,c15).
0::rall100(c15,a15).
0::rsome100(a15,c15).
0::rsome100(c15,a15).
0::rno100(a15,c15).
0::rno100(c15,a15).
0::rsomenot100(a15,c15).
0::rsomenot100(c15,a15).
rsomenot100(c16, a16).
0::rall100(a16,c16).
0::rall100(c16,a16).
0::rsome100(a16,c16).
0::rsome100(c16,a16).
0::rno100(a16,c16).
0::rno100(c16,a16).
0::rsomenot100(a16,c16).
0::rnvc100(a16,c16).
rsome100(c17, a17).
0::rall100(a17,c17).
0::rall100(c17,a17).
0::rsome100(a17,c17).
0::rno100(a17,c17).
0::rno100(c17,a17).
0::rsomenot100(a17,c17).
0::rsomenot100(c17,a17).
0::rnvc100(a17,c17).
rno100(c18, a18).
0::rall100(a18,c18).
0::rall100(c18,a18).
0::rsome100(a18,c18).
0::rsome100(c18,a18).
0::rno100(a18,c18).
0::rsomenot100(a18,c18).
0::rsomenot100(c18,a18).
0::rnvc100(a18,c18).
rsome100(c19, a19).
0::rall100(a19,c19).
0::rall100(c19,a19).
0::rsome100(a19,c19).
0::rno100(a19,c19).
0::rno100(c19,a19).
0::rsomenot100(a19,c19).
0::rsomenot100(c19,a19).
0::rnvc100(a19,c19).
rsomenot100(a20, c20).
0::rall100(a20,c20).
0::rall100(c20,a20).
0::rsome100(a20,c20).
0::rsome100(c20,a20).
0::rno100(a20,c20).
0::rno100(c20,a20).
0::rsomenot100(c20,a20).
0::rnvc100(a20,c20).
rsome100(a21, c21).
0::rall100(a21,c21).
0::rall100(c21,a21).
0::rsome100(c21,a21).
0::rno100(a21,c21).
0::rno100(c21,a21).
0::rsomenot100(a21,c21).
0::rsomenot100(c21,a21).
0::rnvc100(a21,c21).
rno100(c22, a22).
0::rall100(a22,c22).
0::rall100(c22,a22).
0::rsome100(a22,c22).
0::rsome100(c22,a22).
0::rno100(a22,c22).
0::rsomenot100(a22,c22).
0::rsomenot100(c22,a22).
0::rnvc100(a22,c22).
rnvc100(a23, c23).
0::rall100(a23,c23).
0::rall100(c23,a23).
0::rsome100(a23,c23).
0::rsome100(c23,a23).
0::rno100(a23,c23).
0::rno100(c23,a23).
0::rsomenot100(a23,c23).
0::rsomenot100(c23,a23).
rsomenot100(c24, a24).
0::rall100(a24,c24).
0::rall100(c24,a24).
0::rsome100(a24,c24).
0::rsome100(c24,a24).
0::rno100(a24,c24).
0::rno100(c24,a24).
0::rsomenot100(a24,c24).
0::rnvc100(a24,c24).
rnvc100(a25, c25).
0::rall100(a25,c25).
0::rall100(c25,a25).
0::rsome100(a25,c25).
0::rsome100(c25,a25).
0::rno100(a25,c25).
0::rno100(c25,a25).
0::rsomenot100(a25,c25).
0::rsomenot100(c25,a25).
rsome100(a26, c26).
0::rall100(a26,c26).
0::rall100(c26,a26).
0::rsome100(c26,a26).
0::rno100(a26,c26).
0::rno100(c26,a26).
0::rsomenot100(a26,c26).
0::rsomenot100(c26,a26).
0::rnvc100(a26,c26).
rnvc100(a28, c28).
0::rall100(a28,c28).
0::rall100(c28,a28).
0::rsome100(a28,c28).
0::rsome100(c28,a28).
0::rno100(a28,c28).
0::rno100(c28,a28).
0::rsomenot100(a28,c28).
0::rsomenot100(c28,a28).
rsome100(a29, c29).
0::rall100(a29,c29).
0::rall100(c29,a29).
0::rsome100(c29,a29).
0::rno100(a29,c29).
0::rno100(c29,a29).
0::rsomenot100(a29,c29).
0::rsomenot100(c29,a29).
0::rnvc100(a29,c29).
rno100(c30, a30).
0::rall100(a30,c30).
0::rall100(c30,a30).
0::rsome100(a30,c30).
0::rsome100(c30,a30).
0::rno100(a30,c30).
0::rsomenot100(a30,c30).
0::rsomenot100(c30,a30).
0::rnvc100(a30,c30).
rno100(a31, c31).
0::rall100(a31,c31).
0::rall100(c31,a31).
0::rsome100(a31,c31).
0::rsome100(c31,a31).
0::rno100(c31,a31).
0::rsomenot100(a31,c31).
0::rsomenot100(c31,a31).
0::rnvc100(a31,c31).
rall100(c32, a32).
0::rall100(a32,c32).
0::rsome100(a32,c32).
0::rsome100(c32,a32).
0::rno100(a32,c32).
0::rno100(c32,a32).
0::rsomenot100(a32,c32).
0::rsomenot100(c32,a32).
0::rnvc100(a32,c32).
rall100(a34, c34).
0::rall100(c34,a34).
0::rsome100(a34,c34).
0::rsome100(c34,a34).
0::rno100(a34,c34).
0::rno100(c34,a34).
0::rsomenot100(a34,c34).
0::rsomenot100(c34,a34).
0::rnvc100(a34,c34).
rsomenot100(c35, a35).
0::rall100(a35,c35).
0::rall100(c35,a35).
0::rsome100(a35,c35).
0::rsome100(c35,a35).
0::rno100(a35,c35).
0::rno100(c35,a35).
0::rsomenot100(a35,c35).
0::rnvc100(a35,c35).
rno100(a36, c36).
0::rall100(a36,c36).
0::rall100(c36,a36).
0::rsome100(a36,c36).
0::rsome100(c36,a36).
0::rno100(c36,a36).
0::rsomenot100(a36,c36).
0::rsomenot100(c36,a36).
0::rnvc100(a36,c36).
rno100(c37, a37).
0::rall100(a37,c37).
0::rall100(c37,a37).
0::rsome100(a37,c37).
0::rsome100(c37,a37).
0::rno100(a37,c37).
0::rsomenot100(a37,c37).
0::rsomenot100(c37,a37).
0::rnvc100(a37,c37).
rnvc100(a38, c38).
0::rall100(a38,c38).
0::rall100(c38,a38).
0::rsome100(a38,c38).
0::rsome100(c38,a38).
0::rno100(a38,c38).
0::rno100(c38,a38).
0::rsomenot100(a38,c38).
0::rsomenot100(c38,a38).
rsome100(a39, c39).
0::rall100(a39,c39).
0::rall100(c39,a39).
0::rsome100(c39,a39).
0::rno100(a39,c39).
0::rno100(c39,a39).
0::rsomenot100(a39,c39).
0::rsomenot100(c39,a39).
0::rnvc100(a39,c39).
rsomenot100(a40, c40).
0::rall100(a40,c40).
0::rall100(c40,a40).
0::rsome100(a40,c40).
0::rsome100(c40,a40).
0::rno100(a40,c40).
0::rno100(c40,a40).
0::rsomenot100(c40,a40).
0::rnvc100(a40,c40).
rsome100(a41, c41).
0::rall100(a41,c41).
0::rall100(c41,a41).
0::rsome100(c41,a41).
0::rno100(a41,c41).
0::rno100(c41,a41).
0::rsomenot100(a41,c41).
0::rsomenot100(c41,a41).
0::rnvc100(a41,c41).
rsomenot100(c42, a42).
0::rall100(a42,c42).
0::rall100(c42,a42).
0::rsome100(a42,c42).
0::rsome100(c42,a42).
0::rno100(a42,c42).
0::rno100(c42,a42).
0::rsomenot100(a42,c42).
0::rnvc100(a42,c42).
rsome100(a43, c43).
0::rall100(a43,c43).
0::rall100(c43,a43).
0::rsome100(c43,a43).
0::rno100(a43,c43).
0::rno100(c43,a43).
0::rsomenot100(a43,c43).
0::rsomenot100(c43,a43).
0::rnvc100(a43,c43).
rsomenot100(a44, c44).
0::rall100(a44,c44).
0::rall100(c44,a44).
0::rsome100(a44,c44).
0::rsome100(c44,a44).
0::rno100(a44,c44).
0::rno100(c44,a44).
0::rsomenot100(c44,a44).
0::rnvc100(a44,c44).
rno100(a45, c45).
0::rall100(a45,c45).
0::rall100(c45,a45).
0::rsome100(a45,c45).
0::rsome100(c45,a45).
0::rno100(c45,a45).
0::rsomenot100(a45,c45).
0::rsomenot100(c45,a45).
0::rnvc100(a45,c45).
rsome100(a46, c46).
0::rall100(a46,c46).
0::rall100(c46,a46).
0::rsome100(c46,a46).
0::rno100(a46,c46).
0::rno100(c46,a46).
0::rsomenot100(a46,c46).
0::rsomenot100(c46,a46).
0::rnvc100(a46,c46).
rnvc100(a47, c47).
0::rall100(a47,c47).
0::rall100(c47,a47).
0::rsome100(a47,c47).
0::rsome100(c47,a47).
0::rno100(a47,c47).
0::rno100(c47,a47).
0::rsomenot100(a47,c47).
0::rsomenot100(c47,a47).
rnvc100(a48, c48).
0::rall100(a48,c48).
0::rall100(c48,a48).
0::rsome100(a48,c48).
0::rsome100(c48,a48).
0::rno100(a48,c48).
0::rno100(c48,a48).
0::rsomenot100(a48,c48).
0::rsomenot100(c48,a48).
rsomenot100(a49, c49).
0::rall100(a49,c49).
0::rall100(c49,a49).
0::rsome100(a49,c49).
0::rsome100(c49,a49).
0::rno100(a49,c49).
0::rno100(c49,a49).
0::rsomenot100(c49,a49).
0::rnvc100(a49,c49).
rno100(c50, a50).
0::rall100(a50,c50).
0::rall100(c50,a50).
0::rsome100(a50,c50).
0::rsome100(c50,a50).
0::rno100(a50,c50).
0::rsomenot100(a50,c50).
0::rsomenot100(c50,a50).
0::rnvc100(a50,c50).
rsomenot100(a51, c51).
0::rall100(a51,c51).
0::rall100(c51,a51).
0::rsome100(a51,c51).
0::rsome100(c51,a51).
0::rno100(a51,c51).
0::rno100(c51,a51).
0::rsomenot100(c51,a51).
0::rnvc100(a51,c51).
rsomenot100(c54, a54).
0::rall100(a54,c54).
0::rall100(c54,a54).
0::rsome100(a54,c54).
0::rsome100(c54,a54).
0::rno100(a54,c54).
0::rno100(c54,a54).
0::rsomenot100(a54,c54).
0::rnvc100(a54,c54).
rall100(c55, a55).
0::rall100(a55,c55).
0::rsome100(a55,c55).
0::rsome100(c55,a55).
0::rno100(a55,c55).
0::rno100(c55,a55).
0::rsomenot100(a55,c55).
0::rsomenot100(c55,a55).
0::rnvc100(a55,c55).
rsomenot100(c56, a56).
0::rall100(a56,c56).
0::rall100(c56,a56).
0::rsome100(a56,c56).
0::rsome100(c56,a56).
0::rno100(a56,c56).
0::rno100(c56,a56).
0::rsomenot100(a56,c56).
0::rnvc100(a56,c56).
rnvc100(a57, c57).
0::rall100(a57,c57).
0::rall100(c57,a57).
0::rsome100(a57,c57).
0::rsome100(c57,a57).
0::rno100(a57,c57).
0::rno100(c57,a57).
0::rsomenot100(a57,c57).
0::rsomenot100(c57,a57).
rall100(c58, a58).
0::rall100(a58,c58).
0::rsome100(a58,c58).
0::rsome100(c58,a58).
0::rno100(a58,c58).
0::rno100(c58,a58).
0::rsomenot100(a58,c58).
0::rsomenot100(c58,a58).
0::rnvc100(a58,c58).
rsomenot100(a59, c59).
0::rall100(a59,c59).
0::rall100(c59,a59).
0::rsome100(a59,c59).
0::rsome100(c59,a59).
0::rno100(a59,c59).
0::rno100(c59,a59).
0::rsomenot100(c59,a59).
0::rnvc100(a59,c59).
rsome100(a60, c60).
0::rall100(a60,c60).
0::rall100(c60,a60).
0::rsome100(c60,a60).
0::rno100(a60,c60).
0::rno100(c60,a60).
0::rsomenot100(a60,c60).
0::rsomenot100(c60,a60).
0::rnvc100(a60,c60).
rsomenot100(a61, c61).
0::rall100(a61,c61).
0::rall100(c61,a61).
0::rsome100(a61,c61).
0::rsome100(c61,a61).
0::rno100(a61,c61).
0::rno100(c61,a61).
0::rsomenot100(c61,a61).
0::rnvc100(a61,c61).
rno100(c62, a62).
0::rall100(a62,c62).
0::rall100(c62,a62).
0::rsome100(a62,c62).
0::rsome100(c62,a62).
0::rno100(a62,c62).
0::rsomenot100(a62,c62).
0::rsomenot100(c62,a62).
0::rnvc100(a62,c62).
rsome100(a63, c63).
0::rall100(a63,c63).
0::rall100(c63,a63).
0::rsome100(c63,a63).
0::rno100(a63,c63).
0::rno100(c63,a63).
0::rsomenot100(a63,c63).
0::rsomenot100(c63,a63).
0::rnvc100(a63,c63).
