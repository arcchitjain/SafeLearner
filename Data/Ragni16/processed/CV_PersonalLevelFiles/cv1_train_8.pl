base(all8(object, object)).
base(some8(object, object)).
base(no8(object, object)).
base(somenot8(object, object)).
base(rall8(object, object)).
base(rsome8(object, object)).
base(rno8(object, object)).
base(rsomenot8(object, object)).
base(rnvc8(object, object)).
mode(all8(+, +)).
mode(all8(+, -)).
mode(all8(-, +)).
mode(some8(+, +)).
mode(some8(+, -)).
mode(some8(-, +)).
mode(no8(+, +)).
mode(no8(+, -)).
mode(no8(-, +)).
mode(somenot8(+, +)).
mode(somenot8(+, -)).
mode(somenot8(-, +)).

all8(a1, b1).
all8(b1, c1).
no8(a2, b2).
all8(c2, b2).
some8(b3, a3).
all8(b3, c3).
all8(b4, a4).
some8(c4, b4).
somenot8(a5, b5).
some8(c5, b5).
some8(a6, b6).
all8(b6, c6).
no8(b8, a8).
no8(c8, b8).
all8(b10, a10).
some8(b10, c10).
all8(b11, a11).
no8(b11, c11).
somenot8(b12, a12).
somenot8(b12, c12).
all8(a13, b13).
somenot8(c13, b13).
no8(b14, a14).
no8(b14, c14).
all8(b16, a16).
all8(c16, b16).
somenot8(b17, a17).
some8(b17, c17).
some8(b18, a18).
somenot8(c18, b18).
some8(b19, a19).
no8(c19, b19).
some8(b20, a20).
no8(b20, c20).
no8(a21, b21).
somenot8(c21, b21).
no8(a22, b22).
some8(c22, b22).
no8(b23, a23).
all8(b23, c23).
somenot8(b24, a24).
some8(c24, b24).
no8(a25, b25).
no8(c25, b25).
somenot8(b26, a26).
all8(c26, b26).
all8(b27, a27).
somenot8(c27, b27).
some8(a28, b28).
no8(c28, b28).
some8(a29, b29).
some8(c29, b29).
no8(b30, a30).
somenot8(c30, b30).
no8(b31, a31).
somenot8(b31, c31).
somenot8(a32, b32).
no8(b32, c32).
somenot8(b33, a33).
all8(b33, c33).
somenot8(a34, b34).
somenot8(b34, c34).
no8(a35, b35).
some8(b35, c35).
some8(a36, b36).
some8(b36, c36).
some8(b37, a37).
somenot8(b37, c37).
somenot8(b38, a38).
no8(b38, c38).
all8(a39, b39).
some8(c39, b39).
all8(a40, b40).
all8(c40, b40).
no8(a41, b41).
all8(b41, c41).
somenot8(a42, b42).
somenot8(c42, b42).
all8(a43, b43).
somenot8(b43, c43).
all8(a44, b44).
some8(b44, c44).
some8(a45, b45).
no8(b45, c45).
all8(a46, b46).
no8(b46, c46).
all8(a47, b47).
no8(c47, b47).
somenot8(a48, b48).
no8(c48, b48).
all8(b49, a49).
no8(c49, b49).
somenot8(a50, b50).
all8(b50, c50).
some8(a51, b51).
somenot8(b51, c51).
somenot8(a52, b52).
some8(b52, c52).
some8(a53, b53).
all8(c53, b53).
no8(b54, a54).
some8(b54, c54).
no8(b55, a55).
some8(c55, b55).
some8(b56, a56).
some8(b56, c56).
some8(b57, a57).
some8(c57, b57).
all8(b58, a58).
all8(b58, c58).
some8(a59, b59).
somenot8(c59, b59).
no8(b60, a60).
all8(c60, b60).
some8(b61, a61).
all8(c61, b61).
all8(b62, a62).
somenot8(b62, c62).
no8(a63, b63).
no8(b63, c63).
somenot8(b64, a64).
no8(c64, b64).
rall8(a1, c1).
0::rall8(c1,a1).
0::rsome8(a1,c1).
0::rsome8(c1,a1).
0::rno8(a1,c1).
0::rno8(c1,a1).
0::rsomenot8(a1,c1).
0::rsomenot8(c1,a1).
0::rnvc8(a1,c1).
rall8(c2, a2).
0::rall8(a2,c2).
0::rsome8(a2,c2).
0::rsome8(c2,a2).
0::rno8(a2,c2).
0::rno8(c2,a2).
0::rsomenot8(a2,c2).
0::rsomenot8(c2,a2).
0::rnvc8(a2,c2).
rsome8(c3, a3).
0::rall8(a3,c3).
0::rall8(c3,a3).
0::rsome8(a3,c3).
0::rno8(a3,c3).
0::rno8(c3,a3).
0::rsomenot8(a3,c3).
0::rsomenot8(c3,a3).
0::rnvc8(a3,c3).
rsomenot8(c4, a4).
0::rall8(a4,c4).
0::rall8(c4,a4).
0::rsome8(a4,c4).
0::rsome8(c4,a4).
0::rno8(a4,c4).
0::rno8(c4,a4).
0::rsomenot8(a4,c4).
0::rnvc8(a4,c4).
rsome8(a5, c5).
0::rall8(a5,c5).
0::rall8(c5,a5).
0::rsome8(c5,a5).
0::rno8(a5,c5).
0::rno8(c5,a5).
0::rsomenot8(a5,c5).
0::rsomenot8(c5,a5).
0::rnvc8(a5,c5).
rsome8(c6, a6).
0::rall8(a6,c6).
0::rall8(c6,a6).
0::rsome8(a6,c6).
0::rno8(a6,c6).
0::rno8(c6,a6).
0::rsomenot8(a6,c6).
0::rsomenot8(c6,a6).
0::rnvc8(a6,c6).
rsome8(a8, c8).
0::rall8(a8,c8).
0::rall8(c8,a8).
0::rsome8(c8,a8).
0::rno8(a8,c8).
0::rno8(c8,a8).
0::rsomenot8(a8,c8).
0::rsomenot8(c8,a8).
0::rnvc8(a8,c8).
rno8(a10, c10).
0::rall8(a10,c10).
0::rall8(c10,a10).
0::rsome8(a10,c10).
0::rsome8(c10,a10).
0::rno8(c10,a10).
0::rsomenot8(a10,c10).
0::rsomenot8(c10,a10).
0::rnvc8(a10,c10).
rall8(c11, a11).
0::rall8(a11,c11).
0::rsome8(a11,c11).
0::rsome8(c11,a11).
0::rno8(a11,c11).
0::rno8(c11,a11).
0::rsomenot8(a11,c11).
0::rsomenot8(c11,a11).
0::rnvc8(a11,c11).
rsomenot8(c12, a12).
0::rall8(a12,c12).
0::rall8(c12,a12).
0::rsome8(a12,c12).
0::rsome8(c12,a12).
0::rno8(a12,c12).
0::rno8(c12,a12).
0::rsomenot8(a12,c12).
0::rnvc8(a12,c12).
rsomenot8(c13, a13).
0::rall8(a13,c13).
0::rall8(c13,a13).
0::rsome8(a13,c13).
0::rsome8(c13,a13).
0::rno8(a13,c13).
0::rno8(c13,a13).
0::rsomenot8(a13,c13).
0::rnvc8(a13,c13).
rsomenot8(a14, c14).
0::rall8(a14,c14).
0::rall8(c14,a14).
0::rsome8(a14,c14).
0::rsome8(c14,a14).
0::rno8(a14,c14).
0::rno8(c14,a14).
0::rsomenot8(c14,a14).
0::rnvc8(a14,c14).
rno8(a16, c16).
0::rall8(a16,c16).
0::rall8(c16,a16).
0::rsome8(a16,c16).
0::rsome8(c16,a16).
0::rno8(c16,a16).
0::rsomenot8(a16,c16).
0::rsomenot8(c16,a16).
0::rnvc8(a16,c16).
rsomenot8(c17, a17).
0::rall8(a17,c17).
0::rall8(c17,a17).
0::rsome8(a17,c17).
0::rsome8(c17,a17).
0::rno8(a17,c17).
0::rno8(c17,a17).
0::rsomenot8(a17,c17).
0::rnvc8(a17,c17).
rsomenot8(a18, c18).
0::rall8(a18,c18).
0::rall8(c18,a18).
0::rsome8(a18,c18).
0::rsome8(c18,a18).
0::rno8(a18,c18).
0::rno8(c18,a18).
0::rsomenot8(c18,a18).
0::rnvc8(a18,c18).
rno8(c19, a19).
0::rall8(a19,c19).
0::rall8(c19,a19).
0::rsome8(a19,c19).
0::rsome8(c19,a19).
0::rno8(a19,c19).
0::rsomenot8(a19,c19).
0::rsomenot8(c19,a19).
0::rnvc8(a19,c19).
rno8(c20, a20).
0::rall8(a20,c20).
0::rall8(c20,a20).
0::rsome8(a20,c20).
0::rsome8(c20,a20).
0::rno8(a20,c20).
0::rsomenot8(a20,c20).
0::rsomenot8(c20,a20).
0::rnvc8(a20,c20).
rsomenot8(c21, a21).
0::rall8(a21,c21).
0::rall8(c21,a21).
0::rsome8(a21,c21).
0::rsome8(c21,a21).
0::rno8(a21,c21).
0::rno8(c21,a21).
0::rsomenot8(a21,c21).
0::rnvc8(a21,c21).
rall8(c22, a22).
0::rall8(a22,c22).
0::rsome8(a22,c22).
0::rsome8(c22,a22).
0::rno8(a22,c22).
0::rno8(c22,a22).
0::rsomenot8(a22,c22).
0::rsomenot8(c22,a22).
0::rnvc8(a22,c22).
rno8(c23, a23).
0::rall8(a23,c23).
0::rall8(c23,a23).
0::rsome8(a23,c23).
0::rsome8(c23,a23).
0::rno8(a23,c23).
0::rsomenot8(a23,c23).
0::rsomenot8(c23,a23).
0::rnvc8(a23,c23).
rsomenot8(c24, a24).
0::rall8(a24,c24).
0::rall8(c24,a24).
0::rsome8(a24,c24).
0::rsome8(c24,a24).
0::rno8(a24,c24).
0::rno8(c24,a24).
0::rsomenot8(a24,c24).
0::rnvc8(a24,c24).
rnvc8(a25, c25).
0::rall8(a25,c25).
0::rall8(c25,a25).
0::rsome8(a25,c25).
0::rsome8(c25,a25).
0::rno8(a25,c25).
0::rno8(c25,a25).
0::rsomenot8(a25,c25).
0::rsomenot8(c25,a25).
rsomenot8(c26, a26).
0::rall8(a26,c26).
0::rall8(c26,a26).
0::rsome8(a26,c26).
0::rsome8(c26,a26).
0::rno8(a26,c26).
0::rno8(c26,a26).
0::rsomenot8(a26,c26).
0::rnvc8(a26,c26).
rsomenot8(a27, c27).
0::rall8(a27,c27).
0::rall8(c27,a27).
0::rsome8(a27,c27).
0::rsome8(c27,a27).
0::rno8(a27,c27).
0::rno8(c27,a27).
0::rsomenot8(c27,a27).
0::rnvc8(a27,c27).
rall8(c28, a28).
0::rall8(a28,c28).
0::rsome8(a28,c28).
0::rsome8(c28,a28).
0::rno8(a28,c28).
0::rno8(c28,a28).
0::rsomenot8(a28,c28).
0::rsomenot8(c28,a28).
0::rnvc8(a28,c28).
rnvc8(a29, c29).
0::rall8(a29,c29).
0::rall8(c29,a29).
0::rsome8(a29,c29).
0::rsome8(c29,a29).
0::rno8(a29,c29).
0::rno8(c29,a29).
0::rsomenot8(a29,c29).
0::rsomenot8(c29,a29).
rno8(c30, a30).
0::rall8(a30,c30).
0::rall8(c30,a30).
0::rsome8(a30,c30).
0::rsome8(c30,a30).
0::rno8(a30,c30).
0::rsomenot8(a30,c30).
0::rsomenot8(c30,a30).
0::rnvc8(a30,c30).
rno8(c31, a31).
0::rall8(a31,c31).
0::rall8(c31,a31).
0::rsome8(a31,c31).
0::rsome8(c31,a31).
0::rno8(a31,c31).
0::rsomenot8(a31,c31).
0::rsomenot8(c31,a31).
0::rnvc8(a31,c31).
rsome8(c32, a32).
0::rall8(a32,c32).
0::rall8(c32,a32).
0::rsome8(a32,c32).
0::rno8(a32,c32).
0::rno8(c32,a32).
0::rsomenot8(a32,c32).
0::rsomenot8(c32,a32).
0::rnvc8(a32,c32).
rsomenot8(c33, a33).
0::rall8(a33,c33).
0::rall8(c33,a33).
0::rsome8(a33,c33).
0::rsome8(c33,a33).
0::rno8(a33,c33).
0::rno8(c33,a33).
0::rsomenot8(a33,c33).
0::rnvc8(a33,c33).
rsome8(c34, a34).
0::rall8(a34,c34).
0::rall8(c34,a34).
0::rsome8(a34,c34).
0::rno8(a34,c34).
0::rno8(c34,a34).
0::rsomenot8(a34,c34).
0::rsomenot8(c34,a34).
0::rnvc8(a34,c34).
rsomenot8(c35, a35).
0::rall8(a35,c35).
0::rall8(c35,a35).
0::rsome8(a35,c35).
0::rsome8(c35,a35).
0::rno8(a35,c35).
0::rno8(c35,a35).
0::rsomenot8(a35,c35).
0::rnvc8(a35,c35).
rnvc8(a36, c36).
0::rall8(a36,c36).
0::rall8(c36,a36).
0::rsome8(a36,c36).
0::rsome8(c36,a36).
0::rno8(a36,c36).
0::rno8(c36,a36).
0::rsomenot8(a36,c36).
0::rsomenot8(c36,a36).
rnvc8(a37, c37).
0::rall8(a37,c37).
0::rall8(c37,a37).
0::rsome8(a37,c37).
0::rsome8(c37,a37).
0::rno8(a37,c37).
0::rno8(c37,a37).
0::rsomenot8(a37,c37).
0::rsomenot8(c37,a37).
rno8(c38, a38).
0::rall8(a38,c38).
0::rall8(c38,a38).
0::rsome8(a38,c38).
0::rsome8(c38,a38).
0::rno8(a38,c38).
0::rsomenot8(a38,c38).
0::rsomenot8(c38,a38).
0::rnvc8(a38,c38).
rsomenot8(a39, c39).
0::rall8(a39,c39).
0::rall8(c39,a39).
0::rsome8(a39,c39).
0::rsome8(c39,a39).
0::rno8(a39,c39).
0::rno8(c39,a39).
0::rsomenot8(c39,a39).
0::rnvc8(a39,c39).
rnvc8(a40, c40).
0::rall8(a40,c40).
0::rall8(c40,a40).
0::rsome8(a40,c40).
0::rsome8(c40,a40).
0::rno8(a40,c40).
0::rno8(c40,a40).
0::rsomenot8(a40,c40).
0::rsomenot8(c40,a40).
rall8(c41, a41).
0::rall8(a41,c41).
0::rsome8(a41,c41).
0::rsome8(c41,a41).
0::rno8(a41,c41).
0::rno8(c41,a41).
0::rsomenot8(a41,c41).
0::rsomenot8(c41,a41).
0::rnvc8(a41,c41).
rnvc8(a42, c42).
0::rall8(a42,c42).
0::rall8(c42,a42).
0::rsome8(a42,c42).
0::rsome8(c42,a42).
0::rno8(a42,c42).
0::rno8(c42,a42).
0::rsomenot8(a42,c42).
0::rsomenot8(c42,a42).
rsome8(c43, a43).
0::rall8(a43,c43).
0::rall8(c43,a43).
0::rsome8(a43,c43).
0::rno8(a43,c43).
0::rno8(c43,a43).
0::rsomenot8(a43,c43).
0::rsomenot8(c43,a43).
0::rnvc8(a43,c43).
rsome8(a44, c44).
0::rall8(a44,c44).
0::rall8(c44,a44).
0::rsome8(c44,a44).
0::rno8(a44,c44).
0::rno8(c44,a44).
0::rsomenot8(a44,c44).
0::rsomenot8(c44,a44).
0::rnvc8(a44,c44).
rsome8(a45, c45).
0::rall8(a45,c45).
0::rall8(c45,a45).
0::rsome8(c45,a45).
0::rno8(a45,c45).
0::rno8(c45,a45).
0::rsomenot8(a45,c45).
0::rsomenot8(c45,a45).
0::rnvc8(a45,c45).
rall8(c46, a46).
0::rall8(a46,c46).
0::rsome8(a46,c46).
0::rsome8(c46,a46).
0::rno8(a46,c46).
0::rno8(c46,a46).
0::rsomenot8(a46,c46).
0::rsomenot8(c46,a46).
0::rnvc8(a46,c46).
rno8(c47, a47).
0::rall8(a47,c47).
0::rall8(c47,a47).
0::rsome8(a47,c47).
0::rsome8(c47,a47).
0::rno8(a47,c47).
0::rsomenot8(a47,c47).
0::rsomenot8(c47,a47).
0::rnvc8(a47,c47).
rsome8(c48, a48).
0::rall8(a48,c48).
0::rall8(c48,a48).
0::rsome8(a48,c48).
0::rno8(a48,c48).
0::rno8(c48,a48).
0::rsomenot8(a48,c48).
0::rsomenot8(c48,a48).
0::rnvc8(a48,c48).
rno8(c49, a49).
0::rall8(a49,c49).
0::rall8(c49,a49).
0::rsome8(a49,c49).
0::rsome8(c49,a49).
0::rno8(a49,c49).
0::rsomenot8(a49,c49).
0::rsomenot8(c49,a49).
0::rnvc8(a49,c49).
rsome8(c50, a50).
0::rall8(a50,c50).
0::rall8(c50,a50).
0::rsome8(a50,c50).
0::rno8(a50,c50).
0::rno8(c50,a50).
0::rsomenot8(a50,c50).
0::rsomenot8(c50,a50).
0::rnvc8(a50,c50).
rnvc8(a51, c51).
0::rall8(a51,c51).
0::rall8(c51,a51).
0::rsome8(a51,c51).
0::rsome8(c51,a51).
0::rno8(a51,c51).
0::rno8(c51,a51).
0::rsomenot8(a51,c51).
0::rsomenot8(c51,a51).
rnvc8(a52, c52).
0::rall8(a52,c52).
0::rall8(c52,a52).
0::rsome8(a52,c52).
0::rsome8(c52,a52).
0::rno8(a52,c52).
0::rno8(c52,a52).
0::rsomenot8(a52,c52).
0::rsomenot8(c52,a52).
rnvc8(a53, c53).
0::rall8(a53,c53).
0::rall8(c53,a53).
0::rsome8(a53,c53).
0::rsome8(c53,a53).
0::rno8(a53,c53).
0::rno8(c53,a53).
0::rsomenot8(a53,c53).
0::rsomenot8(c53,a53).
rsomenot8(c54, a54).
0::rall8(a54,c54).
0::rall8(c54,a54).
0::rsome8(a54,c54).
0::rsome8(c54,a54).
0::rno8(a54,c54).
0::rno8(c54,a54).
0::rsomenot8(a54,c54).
0::rnvc8(a54,c54).
rsomenot8(c55, a55).
0::rall8(a55,c55).
0::rall8(c55,a55).
0::rsome8(a55,c55).
0::rsome8(c55,a55).
0::rno8(a55,c55).
0::rno8(c55,a55).
0::rsomenot8(a55,c55).
0::rnvc8(a55,c55).
rnvc8(a56, c56).
0::rall8(a56,c56).
0::rall8(c56,a56).
0::rsome8(a56,c56).
0::rsome8(c56,a56).
0::rno8(a56,c56).
0::rno8(c56,a56).
0::rsomenot8(a56,c56).
0::rsomenot8(c56,a56).
rnvc8(a57, c57).
0::rall8(a57,c57).
0::rall8(c57,a57).
0::rsome8(a57,c57).
0::rsome8(c57,a57).
0::rno8(a57,c57).
0::rno8(c57,a57).
0::rsomenot8(a57,c57).
0::rsomenot8(c57,a57).
rall8(a58, c58).
0::rall8(c58,a58).
0::rsome8(a58,c58).
0::rsome8(c58,a58).
0::rno8(a58,c58).
0::rno8(c58,a58).
0::rsomenot8(a58,c58).
0::rsomenot8(c58,a58).
0::rnvc8(a58,c58).
rnvc8(a59, c59).
0::rall8(a59,c59).
0::rall8(c59,a59).
0::rsome8(a59,c59).
0::rsome8(c59,a59).
0::rno8(a59,c59).
0::rno8(c59,a59).
0::rsomenot8(a59,c59).
0::rsomenot8(c59,a59).
rno8(c60, a60).
0::rall8(a60,c60).
0::rall8(c60,a60).
0::rsome8(a60,c60).
0::rsome8(c60,a60).
0::rno8(a60,c60).
0::rsomenot8(a60,c60).
0::rsomenot8(c60,a60).
0::rnvc8(a60,c60).
rsomenot8(a61, c61).
0::rall8(a61,c61).
0::rall8(c61,a61).
0::rsome8(a61,c61).
0::rsome8(c61,a61).
0::rno8(a61,c61).
0::rno8(c61,a61).
0::rsomenot8(c61,a61).
0::rnvc8(a61,c61).
rsome8(c62, a62).
0::rall8(a62,c62).
0::rall8(c62,a62).
0::rsome8(a62,c62).
0::rno8(a62,c62).
0::rno8(c62,a62).
0::rsomenot8(a62,c62).
0::rsomenot8(c62,a62).
0::rnvc8(a62,c62).
rall8(c63, a63).
0::rall8(a63,c63).
0::rsome8(a63,c63).
0::rsome8(c63,a63).
0::rno8(a63,c63).
0::rno8(c63,a63).
0::rsomenot8(a63,c63).
0::rsomenot8(c63,a63).
0::rnvc8(a63,c63).
rno8(c64, a64).
0::rall8(a64,c64).
0::rall8(c64,a64).
0::rsome8(a64,c64).
0::rsome8(c64,a64).
0::rno8(a64,c64).
0::rsomenot8(a64,c64).
0::rsomenot8(c64,a64).
0::rnvc8(a64,c64).
