base(all32(object, object)).
base(some32(object, object)).
base(no32(object, object)).
base(somenot32(object, object)).
base(rall32(object, object)).
base(rsome32(object, object)).
base(rno32(object, object)).
base(rsomenot32(object, object)).
base(rnvc32(object, object)).
mode(all32(+, +)).
mode(all32(+, -)).
mode(all32(-, +)).
mode(some32(+, +)).
mode(some32(+, -)).
mode(some32(-, +)).
mode(no32(+, +)).
mode(no32(+, -)).
mode(no32(-, +)).
mode(somenot32(+, +)).
mode(somenot32(+, -)).
mode(somenot32(-, +)).

all32(a1, b1).
all32(b1, c1).
some32(b2, a2).
all32(b2, c2).
all32(b3, a3).
some32(c3, b3).
no32(a4, b4).
all32(c4, b4).
all32(a5, b5).
some32(c5, b5).
some32(a6, b6).
some32(c6, b6).
some32(b7, a7).
somenot32(c7, b7).
some32(a8, b8).
some32(b8, c8).
somenot32(b9, a9).
somenot32(b9, c9).
somenot32(a10, b10).
some32(c10, b10).
somenot32(b11, a11).
all32(c11, b11).
somenot32(b12, a12).
no32(c12, b12).
no32(a13, b13).
somenot32(b13, c13).
some32(a14, b14).
all32(c14, b14).
no32(a15, b15).
somenot32(c15, b15).
all32(a16, b16).
some32(b16, c16).
no32(b17, a17).
some32(b17, c17).
somenot32(a18, b18).
all32(b18, c18).
no32(b19, a19).
all32(b19, c19).
somenot32(b20, a20).
somenot32(c20, b20).
all32(b21, a21).
no32(b21, c21).
no32(b22, a22).
some32(c22, b22).
all32(b23, a23).
somenot32(c23, b23).
somenot32(a24, b24).
no32(c24, b24).
somenot32(a25, b25).
somenot32(c25, b25).
no32(b26, a26).
no32(c26, b26).
some32(b27, a27).
somenot32(b27, c27).
somenot32(a28, b28).
somenot32(b28, c28).
no32(b29, a29).
somenot32(c29, b29).
somenot32(b30, a30).
no32(b30, c30).
some32(b32, a32).
some32(c32, b32).
somenot32(b33, a33).
all32(b33, c33).
all32(a34, b34).
no32(c34, b34).
some32(b35, a35).
no32(c35, b35).
no32(b36, a36).
somenot32(b36, c36).
all32(a37, b37).
somenot32(b37, c37).
some32(b38, a38).
some32(b38, c38).
somenot32(b39, a39).
some32(c39, b39).
no32(a40, b40).
some32(b40, c40).
all32(b41, a41).
all32(b41, c41).
all32(a42, b42).
all32(c42, b42).
all32(a43, b43).
somenot32(c43, b43).
somenot32(a44, b44).
all32(c44, b44).
no32(a45, b45).
some32(c45, b45).
some32(b47, a47).
all32(c47, b47).
no32(a48, b48).
no32(c48, b48).
no32(a49, b49).
all32(b49, c49).
all32(b50, a50).
somenot32(b50, c50).
somenot32(a51, b51).
no32(b51, c51).
some32(b52, a52).
no32(b52, c52).
all32(a53, b53).
no32(b53, c53).
some32(a54, b54).
no32(c54, b54).
some32(a55, b55).
no32(b55, c55).
no32(b56, a56).
all32(c56, b56).
all32(b57, a57).
no32(c57, b57).
no32(a58, b58).
no32(b58, c58).
no32(b59, a59).
no32(b59, c59).
some32(a60, b60).
all32(b60, c60).
some32(a61, b61).
somenot32(c61, b61).
all32(b62, a62).
all32(c62, b62).
somenot32(b63, a63).
some32(b63, c63).
somenot32(a64, b64).
some32(b64, c64).
rno32(a1, c1).
0::rall32(a1,c1).
0::rall32(c1,a1).
0::rsome32(a1,c1).
0::rsome32(c1,a1).
0::rno32(c1,a1).
0::rsomenot32(a1,c1).
0::rsomenot32(c1,a1).
0::rnvc32(a1,c1).
rno32(c2, a2).
0::rall32(a2,c2).
0::rall32(c2,a2).
0::rsome32(a2,c2).
0::rsome32(c2,a2).
0::rno32(a2,c2).
0::rsomenot32(a2,c2).
0::rsomenot32(c2,a2).
0::rnvc32(a2,c2).
rnvc32(a3, c3).
0::rall32(a3,c3).
0::rall32(c3,a3).
0::rsome32(a3,c3).
0::rsome32(c3,a3).
0::rno32(a3,c3).
0::rno32(c3,a3).
0::rsomenot32(a3,c3).
0::rsomenot32(c3,a3).
rnvc32(a4, c4).
0::rall32(a4,c4).
0::rall32(c4,a4).
0::rsome32(a4,c4).
0::rsome32(c4,a4).
0::rno32(a4,c4).
0::rno32(c4,a4).
0::rsomenot32(a4,c4).
0::rsomenot32(c4,a4).
rsome32(a5, c5).
0::rall32(a5,c5).
0::rall32(c5,a5).
0::rsome32(c5,a5).
0::rno32(a5,c5).
0::rno32(c5,a5).
0::rsomenot32(a5,c5).
0::rsomenot32(c5,a5).
0::rnvc32(a5,c5).
rsomenot32(a6, c6).
0::rall32(a6,c6).
0::rall32(c6,a6).
0::rsome32(a6,c6).
0::rsome32(c6,a6).
0::rno32(a6,c6).
0::rno32(c6,a6).
0::rsomenot32(c6,a6).
0::rnvc32(a6,c6).
rsomenot32(c7, a7).
0::rall32(a7,c7).
0::rall32(c7,a7).
0::rsome32(a7,c7).
0::rsome32(c7,a7).
0::rno32(a7,c7).
0::rno32(c7,a7).
0::rsomenot32(a7,c7).
0::rnvc32(a7,c7).
rno32(c8, a8).
0::rall32(a8,c8).
0::rall32(c8,a8).
0::rsome32(a8,c8).
0::rsome32(c8,a8).
0::rno32(a8,c8).
0::rsomenot32(a8,c8).
0::rsomenot32(c8,a8).
0::rnvc32(a8,c8).
rsomenot32(a9, c9).
0::rall32(a9,c9).
0::rall32(c9,a9).
0::rsome32(a9,c9).
0::rsome32(c9,a9).
0::rno32(a9,c9).
0::rno32(c9,a9).
0::rsomenot32(c9,a9).
0::rnvc32(a9,c9).
rnvc32(a10, c10).
0::rall32(a10,c10).
0::rall32(c10,a10).
0::rsome32(a10,c10).
0::rsome32(c10,a10).
0::rno32(a10,c10).
0::rno32(c10,a10).
0::rsomenot32(a10,c10).
0::rsomenot32(c10,a10).
rnvc32(a11, c11).
0::rall32(a11,c11).
0::rall32(c11,a11).
0::rsome32(a11,c11).
0::rsome32(c11,a11).
0::rno32(a11,c11).
0::rno32(c11,a11).
0::rsomenot32(a11,c11).
0::rsomenot32(c11,a11).
rnvc32(a12, c12).
0::rall32(a12,c12).
0::rall32(c12,a12).
0::rsome32(a12,c12).
0::rsome32(c12,a12).
0::rno32(a12,c12).
0::rno32(c12,a12).
0::rsomenot32(a12,c12).
0::rsomenot32(c12,a12).
rnvc32(a13, c13).
0::rall32(a13,c13).
0::rall32(c13,a13).
0::rsome32(a13,c13).
0::rsome32(c13,a13).
0::rno32(a13,c13).
0::rno32(c13,a13).
0::rsomenot32(a13,c13).
0::rsomenot32(c13,a13).
rsomenot32(a14, c14).
0::rall32(a14,c14).
0::rall32(c14,a14).
0::rsome32(a14,c14).
0::rsome32(c14,a14).
0::rno32(a14,c14).
0::rno32(c14,a14).
0::rsomenot32(c14,a14).
0::rnvc32(a14,c14).
rsome32(a15, c15).
0::rall32(a15,c15).
0::rall32(c15,a15).
0::rsome32(c15,a15).
0::rno32(a15,c15).
0::rno32(c15,a15).
0::rsomenot32(a15,c15).
0::rsomenot32(c15,a15).
0::rnvc32(a15,c15).
rsome32(a16, c16).
0::rall32(a16,c16).
0::rall32(c16,a16).
0::rsome32(c16,a16).
0::rno32(a16,c16).
0::rno32(c16,a16).
0::rsomenot32(a16,c16).
0::rsomenot32(c16,a16).
0::rnvc32(a16,c16).
rno32(c17, a17).
0::rall32(a17,c17).
0::rall32(c17,a17).
0::rsome32(a17,c17).
0::rsome32(c17,a17).
0::rno32(a17,c17).
0::rsomenot32(a17,c17).
0::rsomenot32(c17,a17).
0::rnvc32(a17,c17).
rall32(c18, a18).
0::rall32(a18,c18).
0::rsome32(a18,c18).
0::rsome32(c18,a18).
0::rno32(a18,c18).
0::rno32(c18,a18).
0::rsomenot32(a18,c18).
0::rsomenot32(c18,a18).
0::rnvc32(a18,c18).
rall32(c19, a19).
0::rall32(a19,c19).
0::rsome32(a19,c19).
0::rsome32(c19,a19).
0::rno32(a19,c19).
0::rno32(c19,a19).
0::rsomenot32(a19,c19).
0::rsomenot32(c19,a19).
0::rnvc32(a19,c19).
rsomenot32(a20, c20).
0::rall32(a20,c20).
0::rall32(c20,a20).
0::rsome32(a20,c20).
0::rsome32(c20,a20).
0::rno32(a20,c20).
0::rno32(c20,a20).
0::rsomenot32(c20,a20).
0::rnvc32(a20,c20).
rall32(c21, a21).
0::rall32(a21,c21).
0::rsome32(a21,c21).
0::rsome32(c21,a21).
0::rno32(a21,c21).
0::rno32(c21,a21).
0::rsomenot32(a21,c21).
0::rsomenot32(c21,a21).
0::rnvc32(a21,c21).
rno32(c22, a22).
0::rall32(a22,c22).
0::rall32(c22,a22).
0::rsome32(a22,c22).
0::rsome32(c22,a22).
0::rno32(a22,c22).
0::rsomenot32(a22,c22).
0::rsomenot32(c22,a22).
0::rnvc32(a22,c22).
rsomenot32(a23, c23).
0::rall32(a23,c23).
0::rall32(c23,a23).
0::rsome32(a23,c23).
0::rsome32(c23,a23).
0::rno32(a23,c23).
0::rno32(c23,a23).
0::rsomenot32(c23,a23).
0::rnvc32(a23,c23).
rno32(c24, a24).
0::rall32(a24,c24).
0::rall32(c24,a24).
0::rsome32(a24,c24).
0::rsome32(c24,a24).
0::rno32(a24,c24).
0::rsomenot32(a24,c24).
0::rsomenot32(c24,a24).
0::rnvc32(a24,c24).
rsome32(a25, c25).
0::rall32(a25,c25).
0::rall32(c25,a25).
0::rsome32(c25,a25).
0::rno32(a25,c25).
0::rno32(c25,a25).
0::rsomenot32(a25,c25).
0::rsomenot32(c25,a25).
0::rnvc32(a25,c25).
rall32(c26, a26).
0::rall32(a26,c26).
0::rsome32(a26,c26).
0::rsome32(c26,a26).
0::rno32(a26,c26).
0::rno32(c26,a26).
0::rsomenot32(a26,c26).
0::rsomenot32(c26,a26).
0::rnvc32(a26,c26).
rsome32(a27, c27).
0::rall32(a27,c27).
0::rall32(c27,a27).
0::rsome32(c27,a27).
0::rno32(a27,c27).
0::rno32(c27,a27).
0::rsomenot32(a27,c27).
0::rsomenot32(c27,a27).
0::rnvc32(a27,c27).
rsome32(a28, c28).
0::rall32(a28,c28).
0::rall32(c28,a28).
0::rsome32(c28,a28).
0::rno32(a28,c28).
0::rno32(c28,a28).
0::rsomenot32(a28,c28).
0::rsomenot32(c28,a28).
0::rnvc32(a28,c28).
rnvc32(a29, c29).
0::rall32(a29,c29).
0::rall32(c29,a29).
0::rsome32(a29,c29).
0::rsome32(c29,a29).
0::rno32(a29,c29).
0::rno32(c29,a29).
0::rsomenot32(a29,c29).
0::rsomenot32(c29,a29).
rno32(c30, a30).
0::rall32(a30,c30).
0::rall32(c30,a30).
0::rsome32(a30,c30).
0::rsome32(c30,a30).
0::rno32(a30,c30).
0::rsomenot32(a30,c30).
0::rsomenot32(c30,a30).
0::rnvc32(a30,c30).
rsome32(a32, c32).
0::rall32(a32,c32).
0::rall32(c32,a32).
0::rsome32(c32,a32).
0::rno32(a32,c32).
0::rno32(c32,a32).
0::rsomenot32(a32,c32).
0::rsomenot32(c32,a32).
0::rnvc32(a32,c32).
rsomenot32(c33, a33).
0::rall32(a33,c33).
0::rall32(c33,a33).
0::rsome32(a33,c33).
0::rsome32(c33,a33).
0::rno32(a33,c33).
0::rno32(c33,a33).
0::rsomenot32(a33,c33).
0::rnvc32(a33,c33).
rall32(c34, a34).
0::rall32(a34,c34).
0::rsome32(a34,c34).
0::rsome32(c34,a34).
0::rno32(a34,c34).
0::rno32(c34,a34).
0::rsomenot32(a34,c34).
0::rsomenot32(c34,a34).
0::rnvc32(a34,c34).
rsome32(a35, c35).
0::rall32(a35,c35).
0::rall32(c35,a35).
0::rsome32(c35,a35).
0::rno32(a35,c35).
0::rno32(c35,a35).
0::rsomenot32(a35,c35).
0::rsomenot32(c35,a35).
0::rnvc32(a35,c35).
rnvc32(a36, c36).
0::rall32(a36,c36).
0::rall32(c36,a36).
0::rsome32(a36,c36).
0::rsome32(c36,a36).
0::rno32(a36,c36).
0::rno32(c36,a36).
0::rsomenot32(a36,c36).
0::rsomenot32(c36,a36).
rsomenot32(a37, c37).
0::rall32(a37,c37).
0::rall32(c37,a37).
0::rsome32(a37,c37).
0::rsome32(c37,a37).
0::rno32(a37,c37).
0::rno32(c37,a37).
0::rsomenot32(c37,a37).
0::rnvc32(a37,c37).
rsome32(a38, c38).
0::rall32(a38,c38).
0::rall32(c38,a38).
0::rsome32(c38,a38).
0::rno32(a38,c38).
0::rno32(c38,a38).
0::rsomenot32(a38,c38).
0::rsomenot32(c38,a38).
0::rnvc32(a38,c38).
rall32(c39, a39).
0::rall32(a39,c39).
0::rsome32(a39,c39).
0::rsome32(c39,a39).
0::rno32(a39,c39).
0::rno32(c39,a39).
0::rsomenot32(a39,c39).
0::rsomenot32(c39,a39).
0::rnvc32(a39,c39).
rsomenot32(c40, a40).
0::rall32(a40,c40).
0::rall32(c40,a40).
0::rsome32(a40,c40).
0::rsome32(c40,a40).
0::rno32(a40,c40).
0::rno32(c40,a40).
0::rsomenot32(a40,c40).
0::rnvc32(a40,c40).
rno32(a41, c41).
0::rall32(a41,c41).
0::rall32(c41,a41).
0::rsome32(a41,c41).
0::rsome32(c41,a41).
0::rno32(c41,a41).
0::rsomenot32(a41,c41).
0::rsomenot32(c41,a41).
0::rnvc32(a41,c41).
rall32(a42, c42).
0::rall32(c42,a42).
0::rsome32(a42,c42).
0::rsome32(c42,a42).
0::rno32(a42,c42).
0::rno32(c42,a42).
0::rsomenot32(a42,c42).
0::rsomenot32(c42,a42).
0::rnvc32(a42,c42).
rsomenot32(a43, c43).
0::rall32(a43,c43).
0::rall32(c43,a43).
0::rsome32(a43,c43).
0::rsome32(c43,a43).
0::rno32(a43,c43).
0::rno32(c43,a43).
0::rsomenot32(c43,a43).
0::rnvc32(a43,c43).
rsome32(a44, c44).
0::rall32(a44,c44).
0::rall32(c44,a44).
0::rsome32(c44,a44).
0::rno32(a44,c44).
0::rno32(c44,a44).
0::rsomenot32(a44,c44).
0::rsomenot32(c44,a44).
0::rnvc32(a44,c44).
rsomenot32(c45, a45).
0::rall32(a45,c45).
0::rall32(c45,a45).
0::rsome32(a45,c45).
0::rsome32(c45,a45).
0::rno32(a45,c45).
0::rno32(c45,a45).
0::rsomenot32(a45,c45).
0::rnvc32(a45,c45).
rnvc32(a47, c47).
0::rall32(a47,c47).
0::rall32(c47,a47).
0::rsome32(a47,c47).
0::rsome32(c47,a47).
0::rno32(a47,c47).
0::rno32(c47,a47).
0::rsomenot32(a47,c47).
0::rsomenot32(c47,a47).
rno32(c48, a48).
0::rall32(a48,c48).
0::rall32(c48,a48).
0::rsome32(a48,c48).
0::rsome32(c48,a48).
0::rno32(a48,c48).
0::rsomenot32(a48,c48).
0::rsomenot32(c48,a48).
0::rnvc32(a48,c48).
rall32(c49, a49).
0::rall32(a49,c49).
0::rsome32(a49,c49).
0::rsome32(c49,a49).
0::rno32(a49,c49).
0::rno32(c49,a49).
0::rsomenot32(a49,c49).
0::rsomenot32(c49,a49).
0::rnvc32(a49,c49).
rnvc32(a50, c50).
0::rall32(a50,c50).
0::rall32(c50,a50).
0::rsome32(a50,c50).
0::rsome32(c50,a50).
0::rno32(a50,c50).
0::rno32(c50,a50).
0::rsomenot32(a50,c50).
0::rsomenot32(c50,a50).
rsome32(c51, a51).
0::rall32(a51,c51).
0::rall32(c51,a51).
0::rsome32(a51,c51).
0::rno32(a51,c51).
0::rno32(c51,a51).
0::rsomenot32(a51,c51).
0::rsomenot32(c51,a51).
0::rnvc32(a51,c51).
rsomenot32(c52, a52).
0::rall32(a52,c52).
0::rall32(c52,a52).
0::rsome32(a52,c52).
0::rsome32(c52,a52).
0::rno32(a52,c52).
0::rno32(c52,a52).
0::rsomenot32(a52,c52).
0::rnvc32(a52,c52).
rno32(c53, a53).
0::rall32(a53,c53).
0::rall32(c53,a53).
0::rsome32(a53,c53).
0::rsome32(c53,a53).
0::rno32(a53,c53).
0::rsomenot32(a53,c53).
0::rsomenot32(c53,a53).
0::rnvc32(a53,c53).
rno32(c54, a54).
0::rall32(a54,c54).
0::rall32(c54,a54).
0::rsome32(a54,c54).
0::rsome32(c54,a54).
0::rno32(a54,c54).
0::rsomenot32(a54,c54).
0::rsomenot32(c54,a54).
0::rnvc32(a54,c54).
rno32(c55, a55).
0::rall32(a55,c55).
0::rall32(c55,a55).
0::rsome32(a55,c55).
0::rsome32(c55,a55).
0::rno32(a55,c55).
0::rsomenot32(a55,c55).
0::rsomenot32(c55,a55).
0::rnvc32(a55,c55).
rno32(c56, a56).
0::rall32(a56,c56).
0::rall32(c56,a56).
0::rsome32(a56,c56).
0::rsome32(c56,a56).
0::rno32(a56,c56).
0::rsomenot32(a56,c56).
0::rsomenot32(c56,a56).
0::rnvc32(a56,c56).
rall32(c57, a57).
0::rall32(a57,c57).
0::rsome32(a57,c57).
0::rsome32(c57,a57).
0::rno32(a57,c57).
0::rno32(c57,a57).
0::rsomenot32(a57,c57).
0::rsomenot32(c57,a57).
0::rnvc32(a57,c57).
rno32(c58, a58).
0::rall32(a58,c58).
0::rall32(c58,a58).
0::rsome32(a58,c58).
0::rsome32(c58,a58).
0::rno32(a58,c58).
0::rsomenot32(a58,c58).
0::rsomenot32(c58,a58).
0::rnvc32(a58,c58).
rall32(c59, a59).
0::rall32(a59,c59).
0::rsome32(a59,c59).
0::rsome32(c59,a59).
0::rno32(a59,c59).
0::rno32(c59,a59).
0::rsomenot32(a59,c59).
0::rsomenot32(c59,a59).
0::rnvc32(a59,c59).
rsome32(a60, c60).
0::rall32(a60,c60).
0::rall32(c60,a60).
0::rsome32(c60,a60).
0::rno32(a60,c60).
0::rno32(c60,a60).
0::rsomenot32(a60,c60).
0::rsomenot32(c60,a60).
0::rnvc32(a60,c60).
rsome32(c61, a61).
0::rall32(a61,c61).
0::rall32(c61,a61).
0::rsome32(a61,c61).
0::rno32(a61,c61).
0::rno32(c61,a61).
0::rsomenot32(a61,c61).
0::rsomenot32(c61,a61).
0::rnvc32(a61,c61).
rall32(a62, c62).
0::rall32(c62,a62).
0::rsome32(a62,c62).
0::rsome32(c62,a62).
0::rno32(a62,c62).
0::rno32(c62,a62).
0::rsomenot32(a62,c62).
0::rsomenot32(c62,a62).
0::rnvc32(a62,c62).
rsomenot32(c63, a63).
0::rall32(a63,c63).
0::rall32(c63,a63).
0::rsome32(a63,c63).
0::rsome32(c63,a63).
0::rno32(a63,c63).
0::rno32(c63,a63).
0::rsomenot32(a63,c63).
0::rnvc32(a63,c63).
rsomenot32(c64, a64).
0::rall32(a64,c64).
0::rall32(c64,a64).
0::rsome32(a64,c64).
0::rsome32(c64,a64).
0::rno32(a64,c64).
0::rno32(c64,a64).
0::rsomenot32(a64,c64).
0::rnvc32(a64,c64).
