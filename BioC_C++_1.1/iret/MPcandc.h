#ifndef _MPGR_H
#define _MPGR_H

#include "MPtag.h"

using namespace std;

class MPcandc : public MPtag
{
public:
	MPcandc(string idir = ""): MPtag(idir) { set_segment(0); set_tagset("penn"); };
	~MPcandc() { };

	vector<string> gr;

	void parse(const string&);
private:
	void iparse();
	void iparse(string&);
};
#endif
