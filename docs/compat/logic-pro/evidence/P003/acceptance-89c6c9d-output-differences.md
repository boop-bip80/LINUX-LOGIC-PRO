# Exact 89c6c9d output nondeterminism inventory

Source: `89c6c9d85aba6ed1662035e6366298c92ef9c970`; workflow `41292343355`. Reviewed 2026-11-01T10:04:52.632945+00:00.

Both installations contain 11,941 entries: 9,458 regular files, 1,364 symbolic links and 1,119 directories. There are 9,320 byte-identical regular files and 138 differing files. All 6,447 changed bytes are enumerated below. There are no unexplained installed-byte differences.

Class T: parsed N_OSO object modification timestamps only; all other bytes match. Class V: an exact compile-time version string, its content-derived UUID, and any listed N_OSO timestamps; all other bytes match. These expected build-identification/debug differences do not change the asserted runtime results. The machine-readable companion retains normalized hashes, exact field offsets, source bindings, literal values and acceptance rationale for every row.

| Installed path | Build A SHA256 | Build B SHA256 | Class / changed fields | Changed bytes |
|---|---|---|---|---:|
| `libexec/darling/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation` | `c644dba782e4671aaf864ae8ea57e7ff3484d40c3a6bbf98eee3052331bb0c38` | `4e57fbf6e245dc1f39c892d3d51e6120fa113a04006caf1758062acf5de681a5` | V; 1 LC_UUID; Nov  1 2026 09:27:04 → Nov  1 2026 09:29:02 | 18 |
| `libexec/darling/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit` | `4c01d4b1ebc059dadfcd0d4f03f26650080103b82a1c25dc00fc24757ec6cec7` | `b09bab11ec84c287bff583777e3140401367c4d334fc461441a1898bf1eccbe8` | V; 1 LC_UUID; 09:31:26 Nov  1 2026 → 09:38:10 Nov  1 2026 | 19 |
| `libexec/darling/bin/bash` | `78882a96dac8c3dfa53e4a0fb4276eea19116d5c84572e3f55e4caf92e92ac46` | `8727496f709135a2e582c36ea5aa2d402b38ef1d7ad3903fa9bd226b279098cb` | T; 167 N_OSO_n_value | 334 |
| `libexec/darling/bin/chmod` | `5e41d507c8867f365d6413eb1fc86f5718f0027208707fdaffbbbea37ebbfa27` | `394ccd2e27e106ec4e144d4ce22601945b227b4cc4fb0a6a43a794e230987393` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/bin/cksum` | `5332cd6cb16a91a6004b64cbcdace1af56ed72702eb48d82e1a781e0e98f6878` | `c614e86dd064fe71d3ec374ee3e20f259f3524a1092e8f721cae291445442842` | T; 6 N_OSO_n_value | 12 |
| `libexec/darling/bin/cp` | `df73e6b6f5adbd6f3019ef968519caccd66fdee50633f59bf6c10ea541dc61b5` | `3b4a376b40bb16609b0cbc7838f83ee4ae0a9330a7b42cd842552eb2d7f763e2` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/bin/date` | `7c8f5e3deebc61a72a829f83eea85690f12f4a8d7366511eb078326799e37c59` | `b068b8d987f6cf7fe4ecd72fbe97e64aaf423390e39adb6658c936679a5b3282` | T; 3 N_OSO_n_value | 6 |
| `libexec/darling/bin/dd` | `41c2e8dce568ac16bb494680525186c04646ea12f70d24d96111a6751732004e` | `48e4b93e1e044bae94d24590638fd03144be447a34e99d990bb7e21860f94298` | T; 6 N_OSO_n_value | 12 |
| `libexec/darling/bin/df` | `7241a4d92576ab65ddd0d1f2a55c23ba6fc22f6dc2ae387006bff1504da31310` | `216ac0efc8ec48c220a2eb9e50e9af2e63ebfd778b97735b2d06cf67dbe7a41e` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/bin/du` | `cd833e56277b6cd1cbabae0a4575b50db8608bb0b81d2e527ca00c522826693b` | `e32d53146fb87927e3d1bf55f27aeca87f8428466011cccac9c6e75eff3656ce` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/echo` | `ce036c97e920c7d500cb878256e857b1e269fb95362b56e3f57c79fc26dbd94e` | `6937aaab7a64e8e6c31a183f4b9e3c6884f0e3dbd2a6ee76a89ceb5823585cd7` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/expr` | `b451c8ddac7f99c46f7cc5746b2040ea43c2bf0689722df4eac74a8d0daf20e8` | `605f175b6f4f44235ff2de56f5c487e388ab8d6f7c1f79589cef019b89eb6938` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/grep` | `05f0be602bf4e4940364680e5624471f20b24d62881e0d57fdf7a21f370092b5` | `822af3e4c5fac86e5bfec69ed3e7f48db318a75903b5a9a8aeff53c6d8eb85a3` | T; 28 N_OSO_n_value | 56 |
| `libexec/darling/bin/kill` | `8c8d09cd7ee760c0632eca3715fc24999dc8e970b0845d9fd07bb9e5bc80af8d` | `ada1252553b34751ea1d20a4913b8009fc9d2ebe7a51c854716611d93b6175f2` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/ln` | `420dee484b49cff8e2794d77b8e4349b6f2bf4c0bdaf2200ce8085d51d46fc91` | `e26b6eec855835c063c387ad3a24c26fd2d2751986cb781d18a6fdc028c61d30` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/ls` | `ca2528c6c1aed477f084305a653c9a7045f1a875581299634af38cad5c3c3c7e` | `fdf0def8c27eca9ff6d503edb5059be5c6dca4e1fc20be161b02026585cfe320` | T; 4 N_OSO_n_value | 8 |
| `libexec/darling/bin/mkdir` | `a3ab39472c6f2558b09eb0568fd74318c68f439db7777b83c77e2a8e9c07507f` | `115f60dde81e7b9395f610426c0eee9e481869d04cd6e6a024da7a43e83d75e4` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/mknod` | `59b026e165993ceb8f81b5ab0f1492657dfa42f425755f7c7e9484205fddb023` | `9d758ad8402d950df62f419585020d6c9606bb6790752ee764d256f8ddcbac25` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/mv` | `f2e0505e862961c2db1665d6c9bb37f4314fc7efd6655589c908e02c1ab30ecb` | `b8048da15d942df21c5fe1d79978ae8000dd51dd098f58127809ab241172a1fd` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/pax` | `648e1731b5e4c04a0ba66dd1921f37c5aa4935917a9d63708519334ea1b2a248` | `c8cf051cd823cf71fe682718c5b961d677776d040e7669ced9713865c8c66ae9` | T; 17 N_OSO_n_value | 34 |
| `libexec/darling/bin/ps` | `dfb4d510466f737a74bea4b3927eff6b6769097cee038ecb7e41eebe99e13e58` | `61696b767685915a6255954c4aa574c1dc5f1327922193bddc99a5072e3bb562` | T; 6 N_OSO_n_value | 12 |
| `libexec/darling/bin/pwd` | `04bc0e5c4c72d27b8ab357b93138e46af4274247b2e6ee1492de886ac2a60344` | `95add904bb912ce2df2eeb3d222a346c569d5d4fe94b83d7d076daf0b349e019` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/rm` | `fbbdc095a218cb7f8423325fb5570929f3195b8685ded2f6ccdb08d4c3d6002f` | `12b41f579362ac77dfcd8bbd520b4b53311f84003eaf7777ee3ccad0bab6f6bb` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/rmdir` | `e68e0c71bded70eb46b6bd1ab98d4673979ee056c86f6caa078ad8aabc924de6` | `c3b79e2d4b3fd5cfe7911b85deacac92be8ce6c2018b4ad3038f208b0581d47f` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/sleep` | `8ecc28d7c3a6b4310103c0ca70f3abec9022dc93d257945a5631e44c91a53eb6` | `74790d810f5db6f18f7153d61454634958c820bb0ee158ddb9d60f94508d7737` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/stat` | `5f9bca12b183d4f1767689f4ca1596442c3ab9a24da2aa1947ad6a67ee157256` | `1eb19fe9976b7281217147a6449deb7595027af555991b9d119fe2748ffe8490` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/bin/stty` | `46532d7d5aed3735ad3e242dd4047a6cbe62d939e998e47cba5f9f5ad9e0f4e2` | `878ef902b93955578e04d4f57fc8a87913bf9cfdd54969bf42d3e9324b7cd8d9` | T; 7 N_OSO_n_value | 14 |
| `libexec/darling/bin/test` | `24e2dd44a7491011021d9519deb18fcd0ba866345e20a60a37caefcb7fe6ce6c` | `2f7381612717ea86886233baf536e367b40cf32a88f37b7f774cdc416d24c9c7` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/sbin/ifconfig` | `8917cf741ec5e6316ce085c8491725daa4fc11a3e8c8c42d3ff571a57f2c5c13` | `fab4b102df4097909a41e296bcd8e84fae74d0d18f1df16fd6b9db7f3c8885f4` | T; 12 N_OSO_n_value | 24 |
| `libexec/darling/sbin/netstat` | `061c86fa2542a013fdcb8231b578548b01298ac6c6b5b2ecc1374643dd779806` | `101f99d0cf94dca12040b0b43d0cf72e464261b73c6c6bff765f71f68b39ab5e` | T; 14 N_OSO_n_value | 28 |
| `libexec/darling/sbin/route` | `342d0fa07b75a6efa6ed37f80e291b8d96c9c4d192175960d66b158ed0d9d3f7` | `7e9ee65182b0eabc3f19330105c48aa5a088a4edbfa8cc10d5e1dd21ae194939` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/sbin/rtsol` | `b4fb6a0ade7bd27a3d865382a3f513d41ba93c4da3298aca41ab3e8b0dbe3686` | `d6b00b8f9722ae68ad0c46eeff72452ffb9c2dde8fe827ac53ae91605b6fb13c` | T; 6 N_OSO_n_value | 12 |
| `libexec/darling/usr/bin/apply` | `0b574cd5b061beec29b6a3525960fe96849ce6cb89e1ff85015cf14fd3eab9cf` | `4d71761e2c6f195cce809d59959f16c653b34727d0be4fe7bbf7c22633124655` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/awk` | `0b25e35a35c47f7b98638520ec9f5d741595957ec23ba84a723e30af2533b984` | `3f18788bd60156a8bbfe32d17ce652661add59ae555660a31ed7f9b1a2b155d3` | T; 9 N_OSO_n_value | 18 |
| `libexec/darling/usr/bin/basename` | `43bd223a137eb96d004e115366494007e7343cd0707309ea9bd7f2093403f502` | `f2e28f49ed3669ef91d96fb847d11b84e042040ff8cab59570d5de99be264645` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/cap_mkdb` | `212396b26f39f6310e69a996e76c04600f9af9c20c942bd0f71aca3b6c57151d` | `e763b8ddf54465807c55682fea4a640dcd6d4729b5e09a32d336c66f9e592e36` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/chflags` | `d3343e07ec32a702b61f1d7f384cda02f7715d3385423842d2cada3a2565453e` | `8ccabf793c720899f11b79bdf4dbe3f2fc853d93b1ddd3efeec152185a419d6c` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/compress` | `ab7ce6c5fd73b1046948a434cd6974ea7a2309f2fc05bcebb3b49461f93b0c1d` | `6c9d439a79d3abcb27dacc56e530c7975901a5d40940c0f3b4565138e96072f7` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/bin/delv` | `13cc672d368e613d2ed52b85b7141d428b99dd6b152947fa6be9dfc81feabb1e` | `e7cbe725ee54b7173512069896ebb1987ca01f4514dda3602699e3091e56584e` | T; 159 N_OSO_n_value | 317 |
| `libexec/darling/usr/bin/dig` | `44ffa64fba1e8f8cc67763ecd3a7437e9daaf9107b530109ad63b06a09203742` | `c307d6a5806c6e32cc1260b386d0a05ee9451a81aaf04db612d866de9c02d382` | T; 158 N_OSO_n_value | 314 |
| `libexec/darling/usr/bin/dirname` | `db23eb4b0294c8d3b1d68aa44ec65b0ef3ccfccf6a844ae6b8815ad001e7b577` | `36520cda366dbc535a608ab11e70a4cb299b002b26ee8c8ae6f7f0a4b67ede0b` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/env` | `d87da0553f9bc0147f7b3ae4b285a0dc3abccaa9437e4b0fb1509e1b2ac46951` | `554e9420ed812fcc9d4c270df0a7433d9250588243fe236213c9305aca27e476` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/bin/false` | `da61ea7f1c0c90380ae271f039a4b90a38b3ac39b1dfc603408198efbdeb8b4e` | `f63898f085f9a979bda1e7047b39b30f4f2c66b79ae7510d4b140157e37a173e` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/find` | `4a525720d54fe8e72557ceb73332e0517fc87ae0a309fd4af4a38580c16d3ed0` | `06fd74594cdb5007942d058c4966cc42f7b8ab174c4e73d57649e3e052adf9f4` | T; 8 N_OSO_n_value | 16 |
| `libexec/darling/usr/bin/finger` | `6198c8f62960003d6b24f56ac6df365ad976372392cd230b9d3dbc11e0879244` | `e2c97281edbd952c4faa5274a6183a06e790249f7b1858105bbc2d16b4ff5796` | T; 5 N_OSO_n_value | 10 |
| `libexec/darling/usr/bin/funzip` | `2cae84b2f8b56a20c4db1fd7665442bf8a470e76399ebcc508fae54d220ea609` | `eb0a68b5f89ae13b1b84387d5f64509e67517af54b0bf1a898b2655ad364fb4c` | T; 6 N_OSO_n_value | 12 |
| `libexec/darling/usr/bin/gencat` | `1c86713ea4773b1aafc6526158115cdcd4c2db2753e41e14753d2fa09ed5b90f` | `2e3ae6ba2d6838dea4568dc66a03771aad92f032ed664fa09b27ef079500e2d7` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/bin/getopt` | `6d88c2f9445a5037a4062280adee5533b23984e34bc62a8feebf49723a48c762` | `719631591a1f7ec36e697484231fe9a31a03804f96c49ed959d9b5d894009c76` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/gzip` | `bde246fd89c996228e4b18b889e96d7270b0e6e3218b0ccaba3e135548402280` | `7c5029602ac497d728d229227875684c66731a226797028e4c35dd9617a6e076` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/bin/hexdump` | `9a565673df74f5a3806463347e2da83bb817e0d7968c8cf15461e5f543ac67ae` | `42fb2788b5bc98499b771ee14461e08012dc0de61251192482e9efcad48ae57d` | T; 6 N_OSO_n_value | 12 |
| `libexec/darling/usr/bin/host` | `f5c206cfa1386fc31598a92f325901b988342a8bc93e44b22c255b672e050fa7` | `994e6b4da34a039328a7186d067a5819245ac5c47841227d8599059b1561beff` | T; 159 N_OSO_n_value | 316 |
| `libexec/darling/usr/bin/hostname` | `20ca02fe89785b6285ad7823095b3a10c1f9b8b855d4cec2504b5aaa7847bd1c` | `fff13278d8d75b1b0f40cfff56b585a30fed539cdcb127f103ad4ce81b2be0d1` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/id` | `305ee6230ce8dea77252d5bd30142703d1562fabdd05d27c6efa79f744de932a` | `0be5c773daabd35b8b182d11af3d2dea8c1128eb9a2f040cc006dd19bb29f00b` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/install` | `ea48d066c82baeef09084368543234aa79c06f2707da298a3e09c9d194c74a50` | `481e5b0a951873a0480481afd5fa8eebedd4c0aa0924fec04ea5ae80ae1f2fa3` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/ipcrm` | `4a9055cf410d869e803f25ba2aa87fd34c7a89a55881eac9b15611b4663bef09` | `a10a279ee91c6e0b9ab82f6a4f40cc77d181acd5466ca4eeb2573c3f7c9c75a9` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/jot` | `6d895555aaf3b2edf407f1c8a479ad91961150cfb08d1ff42c9bada956ba8e6a` | `72ac1bc750eae4284d40eb2c7e59161cf4405b460b1039110d1282753df620c6` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/killall` | `893963dda2b7ffb3d3511c2ca677312655fc8a681c02756d2cc5d53e7653b153` | `9194c477db38b65f4e735f95e027e7651a0d7ad7e4deb845685fa62e4824f680` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/last` | `e9d8f8bf82a1f3dfba0ac37582c2651e6a4eed3690462ee13a997ea98e942f03` | `998759713a2b0d43bf58fde503fe549ed9480382bdefdd98065008e29529a888` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/lastcomm` | `62bb905c3fd72ff7005b15d9130d5f5de8c70af21afbc13310c22298238b0773` | `5bb2e9d3987cea0ee9c9822e2226b08e867091ec7b61188ed7abb21f0d613be3` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/less` | `00f059fd33ef1f5c426efd08b0c69b3672af700b42afe2f19cc048b1f6e8d09c` | `a2694755c2041993c21ab62d831d6e1e9abe2dd6b067e2c247e10141b141331f` | T; 33 N_OSO_n_value | 66 |
| `libexec/darling/usr/bin/lessecho` | `ba5bc343e56147016eba0f03bb049cd18260ef41141af1d761ada3ddea16b557` | `5224d7bda66f0d11281a329c509636e6f00d98f252e5259ff068957f2e3d4252` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/locale` | `e71e41bcdb0e1064c5710b9968cfc418c7c23b53d7347768accf33e519a7b536` | `eaffe525985457903f53047c04f306d073bf99612bec088ee81f0736b1320740` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/logname` | `073856ba1f50ecb9b438a126a14d86a6ba775fd14317f89f45ed1676e6db64c3` | `20de71c7fc32d64db04a8703e3c7f361936cf893ef8edd62f29ed06ac08dde2c` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/lsvfs` | `d1611b2826331d93349cba50f34c93b0c2d2d94dbd8b8e38abdd566e0f889fed` | `d5fcde437e22a4b45eb245c155d27ab209dbdcee78148b2c6b13792147deb40e` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/mkfifo` | `58c090ed25feddecdff8cd0f2af27e3e73f58ff54fafcbdeba0bae9a05c22c73` | `ea8292ee0808a9c7d32998227ca97624a187cadfc56f764f6cf856c86fbfefec` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/mklocale` | `77dba1db0858899eee58f4d147f6bc3a109f043527ca13f99ef22eaf5b8a3600` | `5035b491fbb8c33915367e98b6fa3fadd34bcf4c10c887f4fc9efdee14f009f1` | T; 3 N_OSO_n_value | 6 |
| `libexec/darling/usr/bin/mktemp` | `8647806eefa0ba6d17329a0e653d9aa408eca394f395fd14d4d28dd23cfd9459` | `8dba4ed14d1192710f8ab83ecfbd86d390c9d30f585266346010a04222f0cb7d` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/nano` | `543a4b87d080cd2be159650861e88a3cd23043b88567169fc8a29633944f5ff9` | `dc2534436547819be746ca78ddac9e5711c4d28343b42a6d562fc3852133a810` | V; 1 LC_UUID, 15 N_OSO_n_value; 09:30:29 → 09:36:17 | 49 |
| `libexec/darling/usr/bin/nice` | `d8dd2ce217eb597e665cc1692f99913c1939e0d28e7d326b55b800392c30be5e` | `5f2a1cb7bc4ab24d00ec1560c8be25474114f974b263eb124a10fab6b847d17c` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/nohup` | `695181d57c88b3e74ef03bc1897b9e03b13d81550e00aa9b659b702c61136ead` | `c57a5d7e44c79fcdf365edc58f72367a8fa9f9e4d7ed1631ab69dcbdfea22513` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/nslookup` | `0ae06cf8bd02054fd86a4146e108a1fc6462181ec921d849b1ba277961ca412d` | `8150501b03a6a4b21398f6d9e1b8da9ee0bae2468cea877996aee6dacc16e38e` | T; 158 N_OSO_n_value | 314 |
| `libexec/darling/usr/bin/nsupdate` | `5ace9bfaed4af02dd1197f84d1e6c07cb46e8e15fd68367db7eee580dc11e0ad` | `fb1dd8803c776e25b5fefee89021f1c9070b432c8337301ada508793f43e6591` | T; 157 N_OSO_n_value | 313 |
| `libexec/darling/usr/bin/pathchk` | `475d9168c97f04de7607961ec40de014c98e64aafa1e361c6aa79516eb62260c` | `015ac3bedc1221132f414212cafdccdca822252a1d21be02f939933a9617babd` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/printenv` | `6af8ac150d87fb5ee35c1ed2d0c1255afb08521b1f5bbf87750ba7f8bce44309` | `6251a841d6cf0828c40c5ccd06b53f74ce8bc89d70c2b83144c9c1c12b8f1df6` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/printf` | `292eabdf38bd15a6c853e920a02faad01ce1a0a27410fcb93a61ce976b2665e5` | `07bcafaec9290f8fd6dca03f25c02035d79e26cf50f85a989fb43e6d62d7772b` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/renice` | `7f03dec27ff4e29075d73f105ec3fdbb9fe4e7da6cb1540b0901319cbc949bd8` | `31518c163e688c30ed89a3ac9338171ad35bc7da997cc826c897e5089c20114c` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/script` | `6b8168d5dc4b3fab807fa73371964acb66fb505534e55b91e12c7c75eee91349` | `0f4f3b69b39d2645930be3801d0342d22cf57bf3eb9cced2894ab26c6c62e814` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/seq` | `d9068709dd2e5823bf426b672edb16fc713ebae3ee408a64615169ac6a20d0e7` | `231546d602b2be9247c79bfa3c26e1d111e64ecae6c275cb3aa8ade3e36887a4` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/shlock` | `f526252436114d038e00a1643eb1e5656cf78e4b4f8fb16ef5022b95009337c2` | `236855f795156ea89b8e26d266a722c76fc4536cd4d4c7cf12997aebc372ffdc` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/systime` | `cda8a7c301e0b9bc77f672d92c3d9475f15fd4f5ec91aff29988b333e0ba4530` | `4684f43c7e7478d4be6a54c6ec1c122244a2dae050541064702d473bdb309ad1` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/tabs` | `622fc66a233c6a79838d566488c9cb732b066b9f105c794f7c5d87b06224c908` | `b03e5a6804d37baf7c9be091c75ede4633d2b5a9882ae8161e43e57ab81b6ddc` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/tee` | `5fb33ad9b365bc77727f3b2a2e381563b99671495642f42992c87bc73fcfdb18` | `8e35ebe39a1e5de25064012905342bc473ec2f7bc6c352aef9e14719ac250397` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/time` | `924a0dfd8c50537c638b9984b9c596b21f9120ec1403eb76d601474baf3a82d1` | `0129bd859185ca165dfee4ff5463f0940b52ca52f8b9dd1113cd2bbb0285158e` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/touch` | `040b5c1ee013dfb660abd71c677a8b14031805c3fca262d8c55d0cab244da87c` | `494a671544b5666d0faafdabfb15f14140cc33509f07c84b214ff297e09fffaa` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/true` | `ca3ea09e314e60e1df20451c06cff8f0afcc30305c2f2981d786d6bd59fcc61d` | `3a12c3878dd68c9a3029f51d8bfdc149cea1fa68e8a767603a6f631bd48460c1` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/tty` | `fc834ac7974e4174a003adf685cab7202990aa6865ad68080f67e8e2a7012820` | `cb01caf0ca181dd9e3622b60b5c9607effee2850f434dc138928c6198b07e1e9` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/uname` | `a64a4b1bc7b276029fb83ef9c89827eccfb86b2691f68ed99f9010a473bfe9ba` | `9cd072ec990dbd2cba65952df584be1ec3693a3fc61fcba5a2d51be5a9cedd9a` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/unzip` | `8385e1b553e0f22beccfc2e8de7aba06587eecb3950aac2b20bf515187965392` | `71affc4fd78861e11af5b88dbd7d812f1c3e9847dfd41fc7feb9be9688d17af5` | T; 16 N_OSO_n_value | 32 |
| `libexec/darling/usr/bin/unzipsfx` | `8f1ba05eb784d4bd07bb3e4ee8765d70fe01acd9dd5eb0fa1b1c0ad59f967cc4` | `4714835231768250ea17e78f8ae14943f4ecb4231a7413c0bc9c92b47fadac42` | T; 11 N_OSO_n_value | 22 |
| `libexec/darling/usr/bin/users` | `bc59885d73197058ad1d1ff630b70848fe72a7228d37b010beb8b842f0212d97` | `6a432733da7c325640fedf7c077a6acae552f016734f99b8d460c8f43339020d` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/vim` | `97bc1d2137997708518192d858a6e40a63b2457056b69f40a65a8f9addec15bd` | `79859da372d02f2c9df25c68396c3e546c630238c05f66a5fafd234cd6fd50f8` | V; 1 LC_UUID; Nov  1 2026 09:36:13 → Nov  1 2026 09:48:45 | 20 |
| `libexec/darling/usr/bin/what` | `310ef6a45dd6fe3e6fe3bf35bfeeb714b008ba605403ca8963ea256873ee5d75` | `9a98dd23a81195190f9697d17fe9c582b8629f3cb818562f98d27aea2964c9c3` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/whereis` | `d16a5489cec630afb753864a80c226d6c84e4b57cbcf62e7a74d21569d183941` | `10e817f84fff0aa8a7b21cd92b767ad54de62ca9099d0c887e295109e60a576d` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/which` | `396d6ab30d033f51c10df32c915d55545ab442af714540cf096777670d6637c3` | `c3ffaa54b5a88d5cb6a1706db66f4cb5fed621efdfec5315381d39350391b019` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/who` | `ea86262551d91da578709aaac4292eaa0fe993e6ba209e6efc1c29007728e0a1` | `095628f0e38eec359db8bb29a80a59685ec290bcfcc5e8acc081d893e4ea653e` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/bin/whois` | `8147e1253be16b95d931e62b363fe590f3e98a2fe819d762da438e68362bfc4a` | `2d9a32a302b0f1206d71e439f1927f1ce98af794f2d351de6f28ab11e893810c` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/xargs` | `68c44a29a6d3c251c392b642f9e44f365d0e086c645bad5aed9e4117660c4137` | `99afabcf6a22de0bc9c2ef2beefb172492e29ada92fd5f67df0da90a3bb22c36` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/bin/yes` | `bb2dfb896787b48e379e20f0fd87815c15e693a4bdd377c3a3c266a5860ac2de` | `441a756dd91c91d93f3adca4752c61df61309c0e17ab8580373258fd819b0a76` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/bin/zip` | `1b1552480cd5bb71d66e2ed7e1927d1cd42f1d97af1b6468e2254a7f5e62a2a0` | `920c63ca9779c232962f9067e58c45eb21f18d5ebc86b27c74c21bb0664f3f59` | T; 13 N_OSO_n_value | 26 |
| `libexec/darling/usr/bin/zipcloak` | `42f264f49c6ea991d6503b95b2a3318120fd6a78ffdb6a864fb8102bf08f376f` | `0eab9621f2e6eb7da9402e39a59ec41ef6b18599fe0a99d5cdaf0121bc2e4618` | T; 9 N_OSO_n_value | 18 |
| `libexec/darling/usr/bin/zipnote` | `7a5e4db46cdfefe472d2656a6007a4ad473e54ade1e939b408bd31562012eedf` | `155b1adad0e3797894364b85612a614ee5543dc4c44f4587d3c95e888b027821` | T; 8 N_OSO_n_value | 16 |
| `libexec/darling/usr/bin/zipsplit` | `e79075fb197f9dbda6fe27ce6f943ac2c14cdecc2f5e1619381f566f0ac5ea5d` | `c33e285c94c3fb614fe76e0866751390b187f4ea6f8f18821d5517936e61ab14` | T; 8 N_OSO_n_value | 16 |
| `libexec/darling/usr/lib/darling/xtrace-mig/libexc_xtrace_mig.dylib` | `8eba5751e3a0818f9d071cb9447ee5a52d019c0b318a8102c891fefdfb4277c7` | `d82064296d5585c934e5a4c2c5219764dbc37907f806b16714129efe228bd23d` | T; 1 N_OSO_n_value | 1 |
| `libexec/darling/usr/lib/darling/xtrace-mig/libfirehose_reply_xtrace_mig.dylib` | `72d1731fbcc29e18dd09f8ae30474fd4229ea3a10fec0ff575742d46d651706d` | `06230a4c1b597d1a09a80ec067309ec4822201865c7c4b774d1eb77f8806e4c4` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/lib/darling/xtrace-mig/libfirehose_xtrace_mig.dylib` | `a7a3d2b509faca2c6c65ff17d7efa4772b9e45d2b9c05d8c4af5f53c19940824` | `215180dfafacb8adf7ef49d94687ec0df5f928781d1b036d084ffeb079a1a1b0` | T; 1 N_OSO_n_value | 1 |
| `libexec/darling/usr/lib/darling/xtrace-mig/libhelper_xtrace_mig.dylib` | `5d73c10c781d568f2215048b801452890beaf20da0ea73a53dd1be82d5dea197` | `754b786264e4e92374a365f9fb338f40f69be2640fac3725b109fc2d0584d89f` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/lib/darling/xtrace-mig/libjob_xtrace_mig.dylib` | `a8ea4c9ce9962bc3264f96b3f49f07410408bc62c86e8890a92aa71aa591e29f` | `38f765a45c50e0f14c695eced726ab4bc83b1e59a296c3822afb0d6f0bd75f84` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/lib/darling/xtrace-mig/libmach_exc_xtrace_mig.dylib` | `52bfec08ef94988f369331a71f716e6ce71d838f1566ebb4403f199dc95b086c` | `212deb24ec28f24f2837ad17beff609adbc28e6211bca2d6aa06b39d22b502a0` | T; 1 N_OSO_n_value | 1 |
| `libexec/darling/usr/lib/darling/xtrace-mig/libprotocol_xtrace_mig.dylib` | `79906f2cb6c2e94c5b3a5ee1e07a9d8a494308b8fcb337fa0fd4c7edeb3c52b4` | `c9e1e9c9275781624355c4677aecd6f0bf1d3a3e6b9b68aee0c4477094c68e9b` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/lib/dyld` | `77b6984aa2515ebf7a2202569065316ac936628dff2733bf255fbe3bb1d09105` | `e3b6897ea87ae2941348b02dea6095215ddfe71e3b8949fffb8ad0a7a533aff3` | T; 389 N_OSO_n_value | 507 |
| `libexec/darling/usr/lib/libSystem.B.dylib` | `1ffb8fcfa00c2c41c621d38850612fef2a27b2fd0309561361b4d157c3e12914` | `9087e8ee671b7784c3656c1cf5c1682ca2c298a83107a9cd3626a1338e0bc143` | T; 19 N_OSO_n_value | 21 |
| `libexec/darling/usr/lib/libcharset.1.dylib` | `2a7507c6e719aa63b79e37b4d905f8113815a74d3ca7f92315491613cb65339b` | `fd77ce15a939a48eb8c36230f0e025c54d539ffbfa60f14a8fbb7fbe0f9b591f` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/lib/libcrypto.0.9.8.dylib` | `8f0e308d2417e5146d49b7c214f344bb19e8c7e92c07ea2c1c4caa38b35b5929` | `90ad043992bb9a428c365931a51c33dbe9f1782164f5834532842cead27acdce` | T; 495 N_OSO_n_value | 990 |
| `libexec/darling/usr/lib/libiconv.2.dylib` | `d3c86a05aad15cae849460e84a563d1a069f228430a86a6725abd17c92ec1fcf` | `0d28f47f672aae609205a6c3cc5eae772304d4d1a5b87b34619f307c2e2e5069` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/lib/libpmenergy.dylib` | `483918fa2bb8ff780db988bda42ee92a3979fc42315794dc1eec4c44ce6952dd` | `ef214715b23881a5435f6c850dc3e6cdd57bea1400e98f4c51d1c0282d039f26` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/lib/libpmsample.dylib` | `f3c978c6c47f410fd085721f116ceaf834a4568c684ba62429d79c752ae46f78` | `dc6aaac66012a52d8640410f3e623405dea1d8083c9e812b301b0e447c5841f6` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/lib/libssl.0.9.8.dylib` | `4d328f263eb797b51773f0fa9389d8960b959d0bd1d4e15ab70836613d852a7a` | `3082cb4ed48691797fa383f6ea1c7275768b90bf047f9673d5d63b0c8294240e` | T; 44 N_OSO_n_value | 88 |
| `libexec/darling/usr/lib/system/libdispatch.dylib` | `d1256e8cf583e6a0aeb38d7c5a9324bfd855b046e65d91c40ca3e3b0f4ae1fcf` | `cba55976f1529533720833cab7f5900252a10ce167a7339124d76c28b030080d` | T; 26 N_OSO_n_value | 35 |
| `libexec/darling/usr/lib/system/liblaunch.dylib` | `7d4520ca9ebf22cbb596b57d283f6c9a9e57ee6c349a91dd41bc1465519aa644` | `181045768a5a82a650482b016ff8c7fba77ff36cf5b4c34eaf923ab2a431ac67` | T; 5 N_OSO_n_value | 10 |
| `libexec/darling/usr/lib/system/libquarantine.dylib` | `dd9b007e89cff5625440f149ff2cd79329b812c1ea874c0080dfb1a8e1d24e12` | `90bf2c9e0e07dcde48d32a9ba3477ed209c81500a0bad0e7287becfc20fd8c54` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/lib/system/libsystem_c.dylib` | `61040ea15868aeb482491a6634dfd9127bd760e89f484584d0a5f19d4df8d43c` | `22f376acb69e6744e3e4ed9189ad86215d5bf39f52e0df9436d616b5a8c5c579` | T; 624 N_OSO_n_value | 1144 |
| `libexec/darling/usr/lib/system/libsystem_darwin.dylib` | `f71b6f538128fd239d9cff0ad8538438e874ed610026e7e72dca07b919e341fb` | `ff2fefe5e20c1ff983ef4b4e282234c5ea2ca6dabd32b93bfbd83fbcdab3779c` | T; 12 N_OSO_n_value | 24 |
| `libexec/darling/usr/lib/system/libsystem_info.dylib` | `b23d56bb282f92604781ae78700dc1b9e02602ed80f04385967fd7fe202240fc` | `b40bb7a67c5d8c484fe67442209027e5893d5063c097f7f9e3420a0b3ab8b7b5` | T; 105 N_OSO_n_value | 210 |
| `libexec/darling/usr/lib/system/libsystem_kernel.dylib` | `ff78dc79d6c07acdcd0aa49ac2be95063c02ea39cbe607b6689241bcbf6e753a` | `5707684b6c9b6d00ef618de007449fc7fa9da50fe513ab914681de71e96ad73b` | T; 286 N_OSO_n_value | 286 |
| `libexec/darling/usr/lib/system/libsystem_m.dylib` | `e0531234bb6637b4273731d91ac7a57a293081bcbba09f8016ae950ac7a47e49` | `8647d80a9efa701465bb6b2b82c534084196268497f8e97bb9769b5da12c4ed4` | T; 39 N_OSO_n_value | 78 |
| `libexec/darling/usr/lib/system/libunwind.dylib` | `f30b342b550652458881b7c42c87339df04c2a9a9647eee895c3dca8ca3d1672` | `786c71dbb9e7fccd9870fc46b77b0a8999c317817a83c28c5f5c1ff7bf986b5b` | T; 4 N_OSO_n_value | 8 |
| `libexec/darling/usr/libexec/kdumpd` | `d2e343335d9bc45b1d67a81a0ccdde4afb219bcaa824fec5f553d8b5e65d97f3` | `1462cb45b8eda5a389947047215aeb748d62f0535096611c58e78c4d8225dcb5` | T; 2 N_OSO_n_value | 4 |
| `libexec/darling/usr/libexec/path_helper` | `8c79b6340dd120638e24f3a93d203fbd21438082337e3177a4173499fdeca064` | `ebadbc68780c1e6e3757f2845bdaff34ca29b15638cf1aab05d03e53192e56ef` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/sbin/arp` | `5ba58d1dbc73865bd228426a52c4fbd162875fc45506f7097ed0b7a035a4b2e0` | `a90d4ece8c1461f94bbf41a7c04ede7e211295e378957c7575566937346e01a0` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/sbin/chown` | `543b6df19a33c1845400e3c55f72980f890ccbbb923f7494f3a12297c564a1c9` | `cc24c1db312c37fdefda4c97f9b07066eb91b42a4ce5c79a29a4b5beeffd62d6` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/sbin/chroot` | `3d424aab4aeac403888b42e9da7b77c619594b9b0e7465a124a150ba9a48ec70` | `f5974622bb08823493211f7a4473ce4b48af4b55d8f4befb4a91d52a2ba71eb5` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/sbin/ddns-confgen` | `60a2906b76ddf839ded14c43a5773f4d404b7425e6a1d5041b02dd1bf188d6b7` | `85a38aff4a6de7fdd33a5ddc542531bf525365b8722094a9a7049fbc389972d1` | T; 147 N_OSO_n_value | 293 |
| `libexec/darling/usr/sbin/dnctl` | `a88c965251853ded67a1687b5d512ad875cab8681cde44465fe48c2cd793ef24` | `48f0595abae9ef78d7366f2a9f6127113758134ff204021e144e4a587d9772c3` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/sbin/ndp` | `692c1406d921cab958582661125ffd5469aedd6f56103ceb8f37b04b3631b62b` | `c38900d7c8a7e2dc7226a86e55dad5ddf1ba7a2ae0ddbea8d3e8c27c43c6414a` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/sbin/netstat` | `061c86fa2542a013fdcb8231b578548b01298ac6c6b5b2ecc1374643dd779806` | `101f99d0cf94dca12040b0b43d0cf72e464261b73c6c6bff765f71f68b39ab5e` | T; 14 N_OSO_n_value | 28 |
| `libexec/darling/usr/sbin/rarpd` | `c3a7fc56de5013df8bdd39819f9c1be2cef1ba62ab9f503f7a6ba33461ade1bf` | `b73be11550789a6ca1651cb09ec0629d27c87f4589bd72f1e123a8d8172d1b66` | T; 1 N_OSO_n_value | 2 |
| `libexec/darling/usr/sbin/rtadvd` | `470a0fe6f9eb4f1449a4aeafd0d643a9b36c4e9f80b5521ddefcc20aaf04a1c7` | `6f5653cf405412acf31fccb0228c3af912009609c10c889a5a5d67ad1a0d49c2` | T; 8 N_OSO_n_value | 16 |
| `libexec/darling/usr/sbin/traceroute` | `e07877814252e3804a6cecc956e4e346a6616b7499c1b7d2eaaf1ba947f7661a` | `f5710a0fdff1bf5d749657f9be640d3803dcc8b1a185c1f678948aa95d4fe8f1` | T; 5 N_OSO_n_value | 10 |

## Source-built linker outside the installed prefix

Path: `src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld`.

| Build | Recorded binary SHA256 | Recorded BUILD banner |
|---|---|---|
| A | `e9b4903cbb50aeb2a231d926716daefd15f6b73e2356191218993336fc8e803c` | `BUILD 09:25:35 Nov  1 2026` |
| B | `37a753e4a697cf4b70de4eeb39898ca81acef0295aa5d0b4f2b201f8d8512600` | `BUILD 09:26:06 Nov  1 2026` |

Pinned Options.cpp line 4208 prints the compile time and date. The remaining reported banner and supported architectures match exactly. The executable bytes were not archived, so the report enumerates both recorded binary hashes without claiming an exhaustive byte-level classification of that intermediate build output.

Inventory JSON SHA256: `bc52594bc7d31fe502aad54daeb097149bde7df5cbcf24aa0b822c732cadbcfe`. Paired actual-byte review SHA256: `cab2c18a750fbe970b6bf486b0d703dd84970a73043219443a9241b150110e9c`. Exact normalization review SHA256: `601bddde347bd7dafab875cb4e24f3e64bd0361d7bda42d5efb33b930faf8a43`.
