#ifndef _MPTAG_H
#define _MPTAG_H

using namespace std;

#include "MPlex.h"
#include "MPtok.h"

// Maximum number of tags

#define MAX_TAGS 100

// Maximum length of a tag

#define MAX_TLEN 100

// Maximum number of files

#define MAX_FILES 100

// Maximum length of a line to read

#define MAX_LLEN 10000

// Number n of ngrams

#define NGRAMS 2

// A large enough size for most string buffers

#define BUF_SIZE 1000

// Type to use for floating point numbers

// #include "huge.h"
// #define RTYPE huge
#define RTYPE double

#if NGRAMS==2
#define MAX_STATES MAX_TAGS
#elif NGRAMS==3
#define MAX_STATES (MAX_TAGS*MAX_TAGS)
#elif NGRAMS==4
#define MAX_STATES (MAX_TAGS*MAX_TAGS*MAX_TAGS)
#endif

/*! \brief A class to perform tagging using the MedPost tagger
 */

class MPtag : public MPtok
{
public:
	/// \brief A MPtag object, giving the install directory \p idir where data files can be found
	MPtag(const string& idir = "", const string& cnam = "");
	~MPtag();

	void init();			// Initialize (called automatically)
	void init(const string& idir) { option_dir = idir; init(); } // Initialize using specified install directory
	void load();			///< \brief if a sentence has been tokenized, prepare it for tagging

	void merge_idioms();		///< \brief merge idioms into single tokens in a loaded sentence
	void split_idioms();		///< \brief remove merged idioms (and their tags) after tagging

	void print(int);		///< \brief print the sentence with verbosity

	void compute();			///< \brief tag (loaded) string using forward-backward algorithms
	void compute(const string&);	///< \brief tag string forward-backward algorithms
	void viterbi();			///< \brief tag (loaded) string viterbi algorithm
	void viterbi(const string&);	///< \brief tag string viterbi algorithm
	void baseline();		///< \brief tag (loaded) string baseline algorithm
	void baseline(const string&);	///< \brief tag string baseline algorithm

	void normalize();		// Normalize dw

	void translate();		// translate tags of current tagged sentence

	MPlex *lex;			// The lexicon
	double lex_backoff[MAX_TAGS];	// Backoff smoothing
	void backoff(const char *e);	// Backoff to lexicon entry, or NULL
	double add_smoothing;		// Add smoothing

	int	num_tags;		// The number of tags

	char	*sentence;		// A buffer to hold the whole sentence

	double	**dw;			// The d_w(t) for each word and tag
	double	**pr;			// The current tag probability estimates
	double	*count;			// Count of occurences (only if whole word was in lexicon)

	RTYPE	p_sent;			// Probability of sentence

	RTYPE &alpha(int t, int i);	// Access routines
	RTYPE &beta(int t, int i);
	double &delta(int t, int i);
	int &psi(int t, int i);

	RTYPE *alpha_array;		// Alpha, beta, etc
	RTYPE *beta_array;
	double *delta_array;
	int *psi_array;

	double	zero;			// Zeros, etc
	int	z;

	double *count0;
	double *count1;
	double *count2;
	double *count3;
#if NGRAMS>=4
	double *count4;
#endif

	int num_states;			// The number of states
	int end_tag;			// The tag for end-of-sentence

	// The tags

	char tag_str[MAX_TAGS][MAX_TLEN];
	char save_tag[MAX_TLEN];	// A place to save a tag string
	double pr_tag[MAX_TAGS];
	double pr_state[MAX_STATES];
	double pr_trans[MAX_STATES][MAX_STATES];

	int numstringok(char *str);
	void tag_set(char *word, double *dw, const char *tag, int cond);
	void tag_ok(char *word, double *dw, const char *tag, int cond);

	void read_ngrams(const string&);
	void norm_ngrams();
	void smooth_ngrams(void);

	int option_adhoc;

	// set options

	void set_adhoc_none();		///< \brief Do not apply rules constraining possible tags of unknown words
	void set_adhoc_medpost();	///< \brief Apply built-in rules to constrain possible MedPost tags of unknown words
	void set_adhoc_penn();		///< \brief Apply built-in rules to constrain possible Penn Treebank tags of unknown words
	void set_tagset(const string&);	///< \brief Use this tag set (overrides MedPost), possibilities are "penn" and "claws2"

private:
	int tag_initialized;		// is tagger initialized?

	int tag_at(int, int);
	char *tag_to_str(int);
	int str_to_tag(const char *);
	int state_next(int, int);
	int state_prev(int, int);

	string option_tagset;		// translate tags to this tagset
	map<string,string> trans;	// a translation table

	void maxprob();			// internal function to find max prob tags, used by both compute and baseline
};

#endif

