#ifndef _MPLEX_H
#define _MPLEX_H

#include <string>
#include <map>

// using namespace iret;
using namespace std;

// Implement a lexicon.

/*! \brief A class to handle MedPost lexicon
 */

class MPlex
{
public:

	MPlex(int, int, const char *, int);
	~MPlex();

	void add(char *entry);
	void addfile(const char *file);
	void rm(const char *entry);
	void rmfile(const char *file);

	// Return the whole record for a word.

	const char *get(const char *word);

	// Determine if the word (or idiom) is in the lexicon

	int exists(char *word);

	// Return a probability of the tag given the word.
	// This can use any "machine learning" method to give a result

	double get(const char *word, char *tag);
	double scan_lex(const char *entry, char *tag);
	void search_string(char *buff, const char *word);
	double count(char *word);

private:
	int	num_tags;
	map<string,string> tree;
	int	use_codes;
};

#endif
