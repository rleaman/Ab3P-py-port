DEBUG=-g

DEFAULT_MEDPOST_HOME=\"../MedPost\"

CPPFLAGS=-DDEFAULT_MEDPOST_HOME=$(DEFAULT_MEDPOST_HOME)


libiret.a: Ab3P.o AbbrStra.o AbbrvE.o Bnum.o Btree.o DataObj.o FBase.o Hash.o MPcandc.o MPlex.o MPtag.o MPtok.o Nlphr.o Strset.o runn.o UnicodeIretMap.o
	ar rus $@ $?

%.o: %.C
	$(CXX) $(CPPFLAGS) -c $(DEBUG) $< -o $@ -I.

%.o: %.cpp
	$(CXX) $(CPPFLAGS) -c $(DEBUG) $< -o $@ -I.

clean: 
	rm libiret.a *.o
