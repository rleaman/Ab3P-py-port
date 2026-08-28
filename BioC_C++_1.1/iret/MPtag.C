#include <stdio.h>
#include <strings.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>
#include <math.h>
#include <ctype.h>

#include <string>
#include <map>
#include <iostream>
#include <fstream>
#include <algorithm>

#include "MPtag.h"

#define c0 count0[0]
#define c1(i) count1[(i-1) % (num_tags)]
#define c2(i) count2[(i-1) % (num_tags*num_tags)]
#define c3(i) count3[(i-1) % (num_tags*num_tags*num_tags)]
#if NGRAMS>=4
#define c4(i) count4[(i-1) % (num_tags*num_tags*num_tags*num_tags)]
#endif

// Count the transitions from i to j by reducing to n-grams

#define t2(i,j) c2((i-1)*num_tags+((j-1)%num_tags)+1)
#define t3(i,j) c3((i-1)*num_tags+((j-1)%num_tags)+1)
#define t4(i,j) c4((i-1)*num_tags+((j-1)%num_tags)+1)

enum { ADHOC_NONE = 0, ADHOC_MEDPOST, ADHOC_PENN };

void MPtag::set_adhoc_none() { option_adhoc = ADHOC_NONE; }
void MPtag::set_adhoc_medpost() { option_adhoc = ADHOC_MEDPOST; }
void MPtag::set_adhoc_penn() { option_adhoc = ADHOC_PENN; }

static void chomp(char *line)
{
	int     i;

	i = strlen(line) - 1;
	while (i >= 0 && line[i] == '\n' || line[i] == '\r')
		line[i--] = '\0';
}


// Given a state i, return the tag at the position in the n-gram

int MPtag::tag_at(int i, int pos)
{
	i -= 1;
	while (++pos <= 0) i /= num_tags;
	return (i%num_tags);
}

char *MPtag::tag_to_str(int i)
{
	return tag_str[i];
}

int MPtag::str_to_tag(const char *str)
{
	int	i;

	for (i = 0; i < num_tags; ++i)
		if (strcmp(str, tag_str[i]) == 0)
			return i;
	return -1;
}

int MPtag::state_next(int i, int s)
{
#if NGRAMS==2
	return s+1;
#elif NGRAMS==3
	return tag_at(i,0) * num_tags + s+1;
#elif NGRAMS>=4
	return tag_at(i,-1) * num_tags*num_tags + tag_at(i,0)*num_tags + s+1;
#endif
}

int MPtag::state_prev(int i, int s)
{
#if NGRAMS==2
	return s+1;
#elif NGRAMS==3
	return s*num_tags + tag_at(i,-1) + 1;
#elif NGRAMS>=4
	return s*num_tags*num_tags + tag_at(i,-2)*num_tags + tag_at(i,-1) + 1;
#endif
}

void MPtag::read_ngrams(const string& file)
{
	FILE	*fp;
	char	line[BUF_SIZE];
	int	i, j, k;
	double	v;

	fp = fopen(file.c_str(), "r");
	if (fp == NULL)
	{
                cerr << "could not open " << file << endl;
		exit(1);
	}

	fgets(line, BUF_SIZE, fp);
	num_tags = atoi(line);

	k = -1;
	i = j = 0;
	while (fgets(line, BUF_SIZE, fp))
	{
		chomp(line);

		v = atof(line);

		if (k == -1)
		{
			strcpy(tag_to_str(i), line);
			if (i-j >= num_tags-1)
			{
				j = i + 1;
				++k;
			}
		} else if (k == 0)
		{
			count0[0] = v;
			j = i+1;
			k = 1;
		} else if (k == 1)
		{
			count1[i-j] = v;
			if (v <= 0.0)
			{
				printf("tag %s has probability 0.\n", tag_to_str(i-j));
				// exit(1);
			}
			if (i-j >= num_tags-1)
			{
				j = i+1;
				++k;
			}
		} else if (k == 2)
		{
#if 0
			printf("scangram(%s,%s) = count2[%d] = %g\n",
				tag_to_str(tag_at(i-j+1,-1)),
				tag_to_str(tag_at(i-j+1,0)),
				i-j, v);
#endif
			count2[i-j] = v;
			if (i-j >= num_tags*num_tags-1)
			{
				j = i+1;
				++k;
			}
		} else if (k == 3)
		{
			count3[i-j] = v;
			if (i-j >= num_tags*num_tags*num_tags-1)
			{
				j = i+1;
				++k;
			}
#if NGRAMS>=4
		} else if (k == 4)
		{
			count4[i-j] = v;
			if (i-j >= num_tags*num_tags*num_tags*num_tags-1)
			{
				j = i+1;
				++k;
			}
#endif
		}

		++i;
	}

	fclose(fp);

	end_tag = str_to_tag(".");

	for (i = 0; i < num_tags; ++i)
		pr_tag[i] = count1[i] / count0[0];
}

void MPtag::norm_ngrams()
{
	int	j;
	int	i = NGRAMS;

	if (num_tags == 0)
	{
		printf("ngrams must be read prior to init\n");
		exit(0);
	}

	if (i != NGRAMS)
	{
		printf("This version of the tagger was compiled for ``init %d''.\n", NGRAMS);
		i = NGRAMS;
	}

	if (i == 2) num_states = num_tags;
	else if (i == 3) num_states = num_tags * num_tags;
	else if (i == 4) num_states = num_tags * num_tags * num_tags;

	for (i = 1; i <= num_states; ++i)
	{
#if NGRAMS==2
		pr_state[i-1] = (c0 > 0.0) ? c1(i) / c0 : 1.0 / (double) num_states;
#elif NGRAMS==3
		pr_state[i-1] = (c0 > 0.0) ? c2(i) / c0 : 1.0 / (double) num_states;
#elif NGRAMS==4
		pr_state[i-1] = (c0 > 0.0) ? c3(i) / c0 : 1.0 / (double) num_states;
#endif

		for (j = 1; j <= num_states; ++j)
		{
			pr_trans[i-1][j-1] = 0.0;
#if NGRAMS==2
			pr_trans[i-1][j-1] = (c1(i) > 0.0) ? t2(i,j) / c1(i) : 1.0 / (double) num_tags;
#elif NGRAMS==3
			if (tag_at(i,0) == tag_at(j,-1))
				pr_trans[i-1][j-1] = (c2(i) > 0.0) ? t3(i,j) / c2(i) : 1.0 / (double) num_tags;
#elif NGRAMS==4
			if (tag_at(i,0) == tag_at(j,-1) && tag_at(i,-1) == tag_at(j,-2))
				pr_trans[i-1][j-1] = (c3(i) > 0.0) ? t4(i,j) / c3(i) : 1.0 / (double) num_tags;
#endif
		}
	}
}


// Smooth the ngrams

void MPtag::smooth_ngrams()
{

	// Compute discounted probabilities, then backoff

	double *p1 = new double[MAX_TAGS];
	double *p2 = new double[MAX_TAGS*MAX_TAGS];
	double *p3 = new double[MAX_TAGS*MAX_TAGS*MAX_TAGS];

	double	a, b, d;
	double	N, T, Z;

	int	i, j, k, w;

	double p, m;

	N = T = Z = 0;
	for (i = 0; i < num_tags; ++i)
	{
		N += count1[i];
		if (count1[i] > 0) T++; else Z++;
	}
	d = N / (N + T);

	// The discounted probability for the 1-grams is not backed-off

	for (i = 0; i < num_tags; ++i)
		p1[i] = (count1[i] > 0) ? d * count1[i] / count0[0] : (1 - d) / Z;


	// The 2-gram probabilities (i -> j)

	for (i = 0; i < num_tags; ++i)
	{

		N = T = Z = 0;
		for (j = 0; j < num_tags; ++j)
		{
			k = i * num_tags + j;
			N += count2[k];
			if (count2[k] > 0) T++; else Z++;
		}
		d = N > 0 ? N / (N + T) : 0.0;

#if 0
		printf("Discount factor for %s = %g\n", tag_to_str(i), d);
#endif

		a = b = 0.0;
		for (j = 0; j < num_tags; ++j)
		{
			k = i * num_tags + j;

			// Use the discounted probability, if possible, otherwise use
			// the backoff probability. This will be adjusted afterwards to
			// get a probability

			p2[k] = (count2[k] > 0) ? d * count2[k] / count1[i] : p1[j];

			if (count2[k] > 0) a += p2[k]; else b += p2[k];

#if 0
			printf("p2(%s->%s) = %g, count2 = %g\n", tag_to_str(i), tag_to_str(j), p2[k], count2[k]);
#endif
		}

		a = (1.0 - a) / b;
		for (j = 0; j < num_tags; ++j)
		{
			k = i * num_tags + j;

			if (count2[k] == 0) p2[k] *= a;

#if 0
			printf("p2(%s->%s) = %g, count2 = %g\n", tag_to_str(i), tag_to_str(j), p2[k], count2[k]);
#endif
		}
	}

#if NGRAMS > 2
	// The 3-gram probabilities

	for (i = 0; i < num_tags*num_tags; ++i)
	{

		w = i % num_tags;

		N = T = Z = 0;
		for (j = 0; j < num_tags; ++j)
		{
			k = i * num_tags + j;
			N += count3[k];
			if (count3[k] > 0) T++; else Z++;
		}
		d = N > 0 ? N / (N + T) : 0.0;

		a = b = 0.0;
		for (j = 0; j < num_tags; ++j)
		{
			k = i * num_tags + j;

			// Use the discounted probability, if possible, otherwise use
			// the backoff probability. This will be adjusted afterwards to
			// get a probability

			p3[k] = (count3[k] > 0) ? d * count3[k] / count2[i] : p2[w * num_tags + j];

			if (count3[k] > 0) a += p3[k]; else b += p3[k];
		}

		a = (1.0 - a) / b;
		for (j = 0; j < num_tags; ++j)
		{
			k = i * num_tags + j;

			if (count3[k] == 0) p3[k] *= a;
		}
	}
#endif

	m = 0.0;
	for (i = 0; i < num_states; ++i)
	{

#if NGRAMS==2
		p = p1[i];
#elif NGRAMS==3
		if (end_tag == tag_at(i+1,-1))
			p = p2[end_tag * num_tags + tag_at(i+1,0)];
#endif

		if (fabs(p - pr_state[i]) > m)
			m = fabs(p - pr_state[i]);

		pr_state[i] = p;

		for (j = 0; j < num_states; ++j)
		{

#if NGRAMS==2
			p = p2[i * num_tags + j];
#elif NGRAMS==3
			if (tag_at(i+1,0) == tag_at(j+1,-1))
				p = p3[i * num_tags + (j % num_tags)];
			else
				p = 0.0;
#endif

#if 0
			if (p != pr_trans[i][j])
			{
				printf("pr(%s->%s) was %g now %g\n", tag_to_str(i), tag_to_str(j), pr_trans[i][j], p);
			} else
			{
				printf("pr(%s->%s) = %g unch\n", tag_to_str(i), tag_to_str(j), pr_trans[i][j]);
			}
#endif

			if (fabs(p - pr_trans[i][j]) > m)
				m = fabs(p - pr_trans[i][j]);

			pr_trans[i][j] = p;
		}
	}

#if 0
	printf("Maximum absolute difference %g\n", m);
#endif

	delete [] p1;
	delete [] p2;
	delete [] p3;
}


// This is the tagger code

MPtag::MPtag(const string& idir, const string& cnam) : MPtok(idir, cnam)
{
	tag_initialized = 0;

	alpha_array = NULL;
	beta_array = NULL;
	delta_array = NULL;
	psi_array = NULL;
	num_tags = 0;

	add_smoothing = 0.0;
	for (int i = 0; i < MAX_TAGS; ++i)
		lex_backoff[i] = 1.0;

	zero = 0.0;
	z = 0;

	count0 = new double;
	count1 = new double[MAX_TAGS];
	count2 = new double[MAX_TAGS * MAX_TAGS];
	count3 = new double[MAX_TAGS * MAX_TAGS * MAX_TAGS];
#if NGRAMS>=4
	count4 = new double[MAX_TAGS * MAX_TAGS * MAX_TAGS * MAX_TAGS];
#endif

	num_states = 0;
	end_tag = 0;

	option_adhoc = ADHOC_MEDPOST;

	sentence = new char[MAX_LLEN + 1];
	dw = new double*[MAX_WORDS];
	pr = new double*[MAX_WORDS];

	for (int i = 0; i < MAX_WORDS; i++)
	{
		dw[i] = new double[MAX_TAGS];
		pr[i] = new double[MAX_TAGS];
	}

	count = new double[MAX_WORDS];

	lex = NULL;

	init();
}

void MPtag::init(void)
{
	MPtok::init();

	if (tag_initialized) return;

	string fname;

	fname = option_dir + "/medpost" + option_cnam + ".ngrams";
	read_ngrams(fname);
	norm_ngrams();
	smooth_ngrams();

	fname = option_dir + "/medpost" + option_cnam + ".lex";
	lex = new MPlex(num_tags, 30, fname.c_str(), 1);
	backoff("");

	tag_initialized = 1;
}

void MPtag::tag_ok(char *word, double *dw, const char *tag, int cond)
{
	int	i;
	double	m;

	if (str_to_tag(tag) < 0) return;

	if (! cond)
	{
		dw[str_to_tag(tag)] = 0.0;
		m = 0.0;
		for (i = 0; i < num_tags; ++i)
			m += dw[i];

		// m could be 0 here

		for (i = 0; i < num_tags; ++i)
			dw[i] /= m;
	}
}

// Reset the tag and normalize

void MPtag::tag_set(char *word, double *dw, const char *tag, int cond)
{
	int	i;
	double	m;

	if (str_to_tag(tag) < 0) return;

	if (cond)
	{
		// printf("Forcing %s to %s\n", word, tag);
		for (i = 0; i < num_tags; ++i)
			dw[i] = 0.0;
		dw[str_to_tag(tag)] = 1.0;
	} else
	{
		dw[str_to_tag(tag)] = 0.0;
		m = 0.0;
		for (i = 0; i < num_tags; ++i)
			m += dw[i];

		// m could be 0 here

		for (i = 0; i < num_tags; ++i)
			dw[i] /= m;
	}
}

static const char *spelled_numbers[] = {
"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
"twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
"1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "0th",
NULL };

enum {NUMBER_NOTOK=0, NUMBER_OK, NUMBER_DEFINITE, NUMBER_HYPHEN};

int MPtag::numstringok(char *str)
{
	int	i, n, d, h;
	char	buff[MAX_LLEN];

	strcpy(buff, str);
	for (i = 0; i < strlen(buff); ++i) buff[i] = tolower(buff[i]);

	n = d = h = 0;
	for (i = 0; i < strlen(buff); ++i)
	{
		if (strchr("0123456789", buff[i]))
			++d;
		else if ((i == 0 && strchr("=+-", buff[i])) || strchr(",.:", buff[i]))
			++n;
		else if (i > 0 && (buff[i] == '-' || buff[i] == '+'))
			++h;
	}

	// This is a number

	if (d > 0 && d + n == strlen(buff))
		return NUMBER_DEFINITE;

	// This is a hyphenated number

	if (d > 0 && d + n + h == strlen(buff))
		return NUMBER_HYPHEN;

	for (i = 0; spelled_numbers[i]; ++i)
	{
		if (strncmp(buff, spelled_numbers[i], strlen(spelled_numbers[i])) == 0)
		// || (strlen(spelled_numbers[i]) >= strlen(buff) && strcmp(buff - strlen(spelled_numbers[i]), spelled_numbers[i]) == 0))
		{
			// printf("%s could be a spelled number (%d=%s, length %d)\n", buff, i, spelled_numbers[i], strlen(spelled_numbers[i]));
			return NUMBER_OK;
		}
	}

	return NUMBER_NOTOK;
}

// Check the current word store for idioms in the lexicon

#define MAX_IDIOM_SIZE 100
#define MAX_IDIOM 4

void MPtag::merge_idioms()
{
	int	n;
	char	*p;
	char	buff[MAX_IDIOM_SIZE + 1];

	// Next idiom

	for (int i = 0; i < word.size() - 1; i++)
	{
		// check to see if this is a continuation
		// this doesn't require consistency, it
		// simply looks for continuation and keeps
		// up to the last tag

		if (option_new >= 11)
		{
			for (n = 0;
			i + n < word.size() - 1
			&& this->tag[i + n].size() > 0 && this->tag[i + n][this->tag[i + n].size() - 1] == '+';
			n++)
				;
			if (n > 0)
			{
				// this replaces word i with words i to i + n
				// and leaves the tag i
				// however, if it was pretagged
				// then the last tag needs to be retained
				string tmp = this->tag[i + n];
				merge_words(i, n);
				this->tag[i] = tmp;
				continue;
			}
		}

		// Start by putting words together

		buff[0] = '\0';
		for (n = 0;
		n < MAX_IDIOM
		&& i + n < word.size()
		// but stop if any word is pretagged
		&& (option_new >= 11 && (tag[i + n].size() == 0 || tag[i + n] == option_pretag))
		&& strlen(buff) + word[i+n].size() + 1 < MAX_IDIOM_SIZE;
		n++)
		{
			// if this word was given a tag
			// it must be consistent

			if (n > 0) strcat(buff, " ");
			strcat(buff, word[i+n].c_str());
		}

		if (n < 1) break;

		while (p = strrchr(buff, ' '))
		{
			if (lex->exists(buff))
			{
				merge_words(i, n);
				break;
			}
			*p = '\0';
			--n;
		}
	}
}

// Put back idioms

void MPtag::split_idioms()
{
	split_words();
}

void MPtag::load()
{
	if (word.size() > MAX_WORDS)
	{
		printf("Number of words (%d) limited to %d (change and recompile)\n", word.size(), MAX_WORDS);
		exit(1);
	}

	merge_idioms();

	int	i, j, t;
	char	*s;
	const char *entry;
	char	*buff = new char[MAX_LLEN+1];

	// Initialize memory

	if (alpha_array) { delete[] alpha_array; } alpha_array = new RTYPE[(word.size()+1)*MAX_STATES];
	if (beta_array) { delete[] beta_array; } beta_array = new RTYPE[(word.size()+1)*MAX_STATES];
	if (delta_array) { delete[] delta_array; } delta_array = new double[(word.size()+1)*MAX_STATES];
	if (psi_array) { delete[] psi_array; } psi_array = new int[(word.size()+1)*MAX_STATES];

	if (alpha_array == NULL || beta_array == NULL
	|| delta_array == NULL || psi_array == NULL)
	{
		printf("Could not allocate sentence (%d)\n", word.size());
		exit(1);
	}

	// Set the prior probabilities from the lexicon for each word

	for (i = 0; i < word.size(); i++)
	{
		if (option_new < 10)
		{
			// it was pre-tagged, assume that the tag is a lexicon entry!

			if (i < tag.size() && tag[i].size() > 0)
			{
				int j = str_to_tag(tag[i].c_str());
				if (j >= 0)
				{
					for (t = 0; t < num_tags; ++t) dw[i][t] = 0;
					dw[i][j] = 1000;
					count[i] = 1000;
					continue;
				}
			}
			strncpy(buff, word[i].c_str(), MAX_LLEN);
			buff[MAX_LLEN] = '\0';

			// Lower case the first letter only if the remaining letters are all lower case

			if (i == 0)
			{
				for (j = 1; j < strlen(buff); ++j)
					if (! islower(buff[j]))
						break;
				if (j == strlen(buff))
					buff[0] = tolower(buff[0]);
			}

			s = &buff[0];

			if (s == NULL)
			{
				strcpy(buff, "");
				s = &buff[0];
			}

			entry = lex->get(s);
			count[i] = lex->count(s);

			for (t = 0; t < num_tags; ++t)
			{
				dw[i][t] = lex->scan_lex(entry, tag_to_str(t));
#if 0
				printf("%s (%s) %s%s:%g\n", word[i].c_str(), s, "_", tag_to_str(t), dw[i][t]);
#endif
			}

		} else
		{
			string tmp;

			// it was pre-tagged, assume that the tag is a lexicon entry!

			if (i < tag.size() && tag[i].size() > 0 && tag[i] != option_pretag)
			{
				tmp = "_";
				tmp += tag[i];
				entry = tmp.c_str();
				// assume any pre-specified lexicon entry is always definitive
				// by setting the count to the threshold 1000
				count[i] = 1000;
			} else
			{
				strncpy(buff, word[i].c_str(), MAX_LLEN);
				buff[MAX_LLEN] = '\0';

				// Lower case the first letter only if the remaining letters are all lower case

				if (i == 0)
				{
					for (j = 1; j < strlen(buff); ++j)
						if (! islower(buff[j]))
							break;
					if (j == strlen(buff))
						buff[0] = tolower(buff[0]);
				}

				s = &buff[0];

				if (s == NULL)
				{
					strcpy(buff, "");
					s = &buff[0];
				}

				entry = lex->get(s);
				count[i] = lex->count(s);
			}

			for (t = 0; t < num_tags; ++t)
			{
				dw[i][t] = lex->scan_lex(entry, tag_to_str(t));
#if 0
				printf("%s (%s) %s%s:%g\n", word[i].c_str(), s, "_", tag_to_str(t), dw[i][t]);
#endif
			}
		}
	}

	// Normalize the probabilities
	normalize();

	// Check post-lexicon constraints

	if (option_adhoc != ADHOC_NONE)
	{
		char	essential[MAX_LLEN];
		int	ok, flag;

		for (i = 0; i < word.size(); i++)
		{
			strncpy(buff, word[i].c_str(), MAX_LLEN);
			buff[MAX_LLEN] = '\0';

			if (count[i] > 999.0) continue;	// This means the lexicon entry is definite.

			tag_set(buff, dw[i], "$", strcmp(buff, "$") == 0);
			tag_set(buff, dw[i], "''", strcmp(buff, "'") == 0 || strcmp(buff, "''") == 0);
			tag_set(buff, dw[i], "(", strcmp(buff, "(") == 0 || strcmp(buff, "[") == 0 || strcmp(buff, "{") == 0);
			tag_set(buff, dw[i], ")", strcmp(buff, ")") == 0 || strcmp(buff, "]") == 0 || strcmp(buff, "}") == 0);
			tag_set(buff, dw[i], ",", strcmp(buff, ",") == 0);
			tag_set(buff, dw[i], ".", strcmp(buff, ".") == 0 || strcmp(buff, "!") == 0 || strcmp(buff, "?") == 0);
			tag_set(buff, dw[i], ":", strcmp(buff, "-") == 0 || strcmp(buff, "--") == 0 || strcmp(buff, ":") == 0 || strcmp(buff, ";") == 0);
			tag_set(buff, dw[i], "``", strcmp(buff, "`") == 0 || strcmp(buff, "``") == 0);

			// Numbers are easily recognized,
			// Verbs cannot be hyphenated, this takes care of hyphenated participles
			// which must be tagged as JJ
			// These are the only tags with constraints (so far) that are different
			// in the MedPost and Penn treebank tag set

			if (option_adhoc == ADHOC_MEDPOST)
			{
				switch (numstringok(buff)) {
				case NUMBER_DEFINITE: tag_set(buff, dw[i], "MC", 1); break;
				case NUMBER_OK: tag_ok(buff, dw[i], "MC", 1); break;
				case NUMBER_HYPHEN: tag_set(buff, dw[i], "MC", 1); break;
				default: tag_ok(buff, dw[i], "MC", 0); break;
				}

				tag_ok(buff, dw[i], "VVB", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VVD", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VVG", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VVI", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VVN", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VVZ", strchr(buff, '-') == NULL);
			} else if (option_adhoc == ADHOC_PENN)
			{
				switch (numstringok(buff)) {
				case NUMBER_DEFINITE: tag_set(buff, dw[i], "CD", 1); break;
				case NUMBER_OK: tag_ok(buff, dw[i], "CD", 1); break;
				case NUMBER_HYPHEN: tag_set(buff, dw[i], "CD", 1); break;
				default: tag_ok(buff, dw[i], "CD", 0); break;
				}

				tag_ok(buff, dw[i], "VBP", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VBD", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VBG", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VB", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VBN", strchr(buff, '-') == NULL);
				tag_ok(buff, dw[i], "VBZ", strchr(buff, '-') == NULL);
			}

			// If the word is hyphenated, look at the last word, call this
			// the essential word

			s = strrchr(buff, '-');
			if (s == NULL || strlen(s) < 3) s = &buff[0]; else ++s;
			strcpy(essential, s);

			// If the essential word has at least one letter, and has an embedded cap
			// or number, make it an NN or NNS. NNP is possible but we accept this error.

			ok = 0;
			flag = 0;
			for (j = 0; j < strlen(essential); ++j)
			{
				if ((j > 0 && isupper(essential[j])) || isdigit(essential[j])) flag = 1;
				if (isalpha(essential[j])) ok = 1;
			}
			if (flag == 1 && j > 0 && essential[j - 1] == 's') flag = 2;
			if (ok == 1 && flag == 1) tag_set(buff, dw[i], "NN", 1);
			if (ok == 1 && flag == 2) tag_set(buff, dw[i], "NNS", 1);

			// Require any NNP to be capitalized

			tag_ok(buff, dw[i], "NNP", isupper(essential[0]));

#if 0
			for (t = 0; t < num_tags; ++t)
				printf("%s%s%s:%g after constraints\n", buff, "_", tag_to_str(t), dw[i][t]);
#endif

		}
	}

	// Initialize the tag probabilities

	for (i = 0; i < word.size(); i++)
		for (t = 0; t < num_tags; ++t)
			pr[i][t] = dw[i][t];

	delete[] buff;
}

MPtag::~MPtag()
{
	if (alpha_array) delete[] alpha_array;
	if (beta_array) delete[] beta_array;
	if (delta_array) delete[] delta_array;
	if (psi_array) delete[] psi_array;

	delete[] sentence;

	for (int i = 0; i < MAX_WORDS; i++)
	{
		delete[] dw[i];
		delete[] pr[i];
	}
	delete[] dw;
	delete[] pr;

	delete[] count;
	delete count0;
	delete[] count1;
	delete[] count2;
	delete[] count3;

	delete lex;
}

void MPtag::backoff(const char *e)
{
	if (e) e = lex->get(e);
	for (int t = 0; t < num_tags; ++t)
		lex_backoff[t] = e ? lex->scan_lex(e, tag_to_str(t)) : 1.0;
}

RTYPE &MPtag::alpha(int t, int i)
{
	if (i < 1 || i > num_states) return (RTYPE&) zero = 0.0;
	return alpha_array[(t-1) * num_states + (i-1)];
}

RTYPE &MPtag::beta(int t, int i)
{
	if (i < 1 || i > num_states) return (RTYPE&) zero = 0.0;
	return beta_array[(t-1) * num_states + (i-1)];
}

double &MPtag::delta(int t, int i)
{
	if (i < 1 || i > num_states) return zero = 0.0;
	return delta_array[(t-1) * num_states + (i-1)];
}

int &MPtag::psi(int t, int i)
{
	if (i < 1 || i > num_states) return z = 0;
	return psi_array[(t-1) * num_states + (i-1)];
}

void MPtag::print(int how)
{
	int	i, j;
	double	v;

	if (how == 1)
	{
		printf("sentence log10 probability %g\n", p_sent);

		for (i = 0; i < word.size(); ++i)
		{
			printf("%s", word[i].c_str());

			for (j = 0; j < num_tags; ++j)
			{
				v = floor(0.5 + 100.0 * pr[i][j]) / 100.0;
				if (v > 0)
				{
					printf("%s%s", "_", tag_to_str(j));
					printf(":%g", v);
				}
			}
			printf("\n");
		}
	} else
	{
		MPtok::print(how);
	}
}

// This is where smoothing should be performed!
// To this end, the sentence should retrieve default
// back-off probabilities

void MPtag::normalize()
{
	int	i, t;
	double	T, N, Z, d, sum;
	int	known;

	for (i = 0; i < word.size(); ++i)
	{
		N = T = Z = 0.0;
		for (t = 0; t < num_tags; ++t)
		{
			N += dw[i][t];
			if (dw[i][t] > 0.0) T++; else Z += lex_backoff[t];
		}

		d = N / (N + T);

		// If the word was seen enough (or if it was manually tagged)
		// then don't back off, but average with an insignificant amount
		// of the backoff in case it is needed to break ties.

#define INSIGNIF (10e-10)

		known = (count[i] > 999.0 || N > 999.0);

		if (known) d = 1.0 - INSIGNIF;

		// Witten-Bell smoothing with uniform backoff priors

		sum = 0.0;
		for (t = 0; t < num_tags; ++t)
		{
#if 0
			if (dw[i][t] > 0) printf("%s %s%s:%g before\n", word[i].c_str(), "_", tag_to_str(t), dw[i][t]);
#endif

			if (add_smoothing != 0.0)
			{
				if (add_smoothing > 0.0)
					dw[i][t] = (dw[i][t] + add_smoothing) / (N + add_smoothing * (double) num_tags);
			} else if (known)
			{
				if (N > 0.0 && dw[i][t] > 0.0)
					dw[i][t] = d * dw[i][t] / N;
				else
					dw[i][t] = 0.0;
				if (Z > 0.0 && dw[i][t] > 0.0)
					dw[i][t] += (1.0 - d) * lex_backoff[t] / Z;
			} else
			{
				if (N > 0.0 && dw[i][t] > 0.0) dw[i][t] = d * dw[i][t] / N;
				else if (Z > 0.0) dw[i][t] = (1.0 - d) * lex_backoff[t] / Z;
				else dw[i][t] = 0.0;
			}
			sum += dw[i][t];
#if 0
			if (dw[i][t] > 0) printf("%s %s%s:%g after\n", word[i].c_str(), "_", tag_to_str(t), dw[i][t]);
#endif
		}

		if (sum == 0.0)
		{
			printf("Cannot continue because word '%s' has no possible tags.\n", word[i].c_str());
			exit(1);
		}
	}
}

void MPtag::compute(const string& str)
{
	tokenize(str);
	if (word.size() == 0) return;
	load();
	compute();
}

void MPtag::compute()
{
	int	r, i, j, k;
	double	m, v;
	double	scale;

	// Compute alpha

	p_sent = 0.0;
	for (r = 1; r <= word.size(); ++r)
	{
		// printf("computing alpha(%d/%d)\n", r, word.size());
		scale = 0.0;

		for (i = 1; i <= num_states; ++i)
		{
			alpha(r, i) = 0.0;

			if (dw[r-1][tag_at(i,0)] <= 0.0) continue;

			if (r == 1)
			{
				// if (tag_at(i,-1) == end_tag)
					alpha(r, i) = pr_state[i-1] * dw[r-1][tag_at(i,0)] / pr_tag[tag_at(i,0)];
			} else
			{
				for (k = 0; k < num_tags; ++k)
				{
					j = state_prev(i, k);
					alpha(r,i) += alpha(r-1,j)
						* (RTYPE) (pr_trans[j-1][i-1] * dw[r-1][tag_at(i,0)] / pr_tag[tag_at(i,0)]);
#if 0
// if (alpha(r-1,j) > 0.0)
	printf("(%s %s) -> (%s %s), a=%g, dw=%g\n",
		tag_to_str(tag_at(j,-1)),
		tag_to_str(tag_at(j,0)),
		tag_to_str(tag_at(i,-1)),
		tag_to_str(tag_at(i,0)),
		pr_trans[j-1][i-1], dw[r-1][tag_at(i,0)]);
#endif
				}
			}
#if 0
// if (alpha(r,i) > 0.0)
	printf("alpha(%d,%d) = %g (%s%s%s)\n", r, i, log10(alpha(r,i)), word[r-1].c_str(), "_", tag_to_str(tag_at(i,0)));
#endif

			scale += alpha(r, i);
		}

		for (i = 1; i <= num_states; i++)
			alpha(r, i) /= scale;

		p_sent += log10(scale);
	}

#if 0
	printf("p_sent = %g, num_states = %d\n", p_sent, num_states);
#endif

	// Compute beta

	for (r = word.size(); r >= 1; --r)
	{
		scale = 0.0;
		for (i = 1; i <= num_states; ++i)
		{
			beta(r, i) = 0.0;

			if (r == word.size())
				beta(r, i) = 1.0;
			else
			{
				for (k = 0; k < num_tags; ++k)
				{
					j = state_next(i, k);
					beta(r,i) += ((RTYPE) (pr_trans[i-1][j-1] * dw[r][tag_at(j,0)] / pr_tag[tag_at(j,0)]))
						* beta(r+1, j);
				}
			}

			scale += beta(r, i);
		}

		for (i = 1; i <= num_states; i++)
			beta(r, i) /= scale;
	}

	// Compute maximum likelihood for each tag, and normalize!

	for (r = 1; r <= word.size(); ++r)
	{
		for (i = 0; i < num_tags; ++i)
			pr[r-1][i] = 0.0;

		v = 0.0;
		for (i = 1; i <= num_states; ++i)
		{
			pr[r-1][tag_at(i,0)] += alpha(r,i)*beta(r,i);
			v += pr[r-1][tag_at(i,0)];
		}

		for (i = 0; i < num_tags; ++i)
			pr[r-1][i] /= v;
	}

	maxprob();

#if 0
	printf("Log probability of sentence: %g (prob %g)\n", log10(p_sent), p_sent);
	for (r = 0; r < word.size(); ++r)
		printf("%s%s%s\n", word[r].c_str(), "_", tag[r]);
#endif
}

// #define DEBUG

#define VSCALE

void MPtag::viterbi(const string& str)
{
	tokenize(str);
	if (word.size() == 0) return;
	load();
	viterbi();
}

void MPtag::viterbi()
{
	int	i, j, k, r, p;
	double	m, max_delta;
#ifdef VSCALE
	double scale = 0.0;
#endif

	r = 1;
	for (i = 1; i <= num_states; ++i)
	{
#ifdef VSCALE
		delta(r, i) = pr_state[i-1] * dw[r-1][tag_at(i,0)] / pr_tag[tag_at(i,0)];
		if (delta(r, i) > scale)
		{
			scale = delta(r, i);
		}
#else
		delta(r, i) = log10(pr_state[i-1] * dw[r-1][tag_at(i,0)] / pr_tag[tag_at(i,0)]);
#endif
		psi(r, i) = 0;

#if 0
		printf("delta(%d,%s) = %g\n", r, tag_to_str(tag_at(i,0)), delta(r,i));
		printf("pr_state(%s) = %g\n", tag_to_str(tag_at(i,0)), pr_state[i-1]);
		printf("dw[%s][%s] = %g\n", word[r-1].c_str(), tag_to_str(tag_at(i,0)), dw[r-1][tag_at(i,0)]);
		printf("count1[%s] = %g\n", tag_to_str(tag_at(i,0)), count1[tag_at(i,0)]);
#endif
	}

#ifdef VSCALE
	if (scale > 0.0)
		for (i = 1; i <= num_states; ++i)
			delta(r, i) /= scale;
#endif

	for (r = 2; r <= word.size(); ++r)
	{
		// printf("viterbi(delta(%d,*))\n", r);

#ifdef VSCALE
		scale = 0.0;
#endif

		for (j = 1; j <= num_states; ++j)
		{
#ifdef VSCALE
			max_delta = 0.0;
#else
			max_delta = -1.0e100;
#endif
			p = -1;

			for (k = 0; k < num_tags; ++k)
			{
				i = state_prev(j, k);

#ifdef VSCALE
				m = delta(r-1,i) * pr_trans[i-1][j-1] * dw[r-1][tag_at(j,0)] / pr_tag[tag_at(j,0)];
#else
				m = delta(r-1,i) + log10(pr_trans[i-1][j-1] * dw[r-1][tag_at(j,0)] / pr_tag[tag_at(j,0)]);
#endif
#if 0
			printf("r=%d i=%d j=%d delta=%g pr_trans=%g tag_at=%d dw=%g pr_tag=%g\n",
			r, i, j, delta(r-1,i), pr_trans[i-1][j-1], tag_at(j,0), dw[r-1][tag_at(j,0)], pr_tag[tag_at(j,0)]);
#endif

				if (m > max_delta)
				{
					max_delta = m;
					p = i;
				}
			}
			if (p < 1) p = 1;

			delta(r, j) = max_delta;
			psi(r, j) = p;

#ifdef VSCALE
			if (delta(r, j) > scale)
				scale = delta(r, j);
#endif
		}

#ifdef VSCALE
		if (scale > 0.0)
			for (j = 1; j <= num_states; ++j)
				delta(r, j) /= scale;
#endif
	}

	max_delta = delta(word.size(), 1);
	p = 1;
	for (i = 1; i <= num_states; ++i)
	{
		m = delta(word.size(), i);
		if (m > max_delta)
		{
			max_delta = m;
			p = i;
		}
	}
	tag[word.size()-1] = tag_to_str(tag_at(p, 0));
	for (r = word.size()-1; r > 0; --r)
	{
		p = psi(r+1, p);
		tag[r-1] = tag_to_str(tag_at(p, 0));
	}

	translate();

#if 0
	for (r = 0; r < word.size(); ++r)
		printf("%s%s%s\n", word[r].c_str(), "_", tag[r]);
#endif
}

void MPtag::baseline(const string& str)
{
	tokenize(str);
	if (word.size() == 0) return;
	load();
	baseline();
}

void MPtag::baseline()
{
	int	i, j;

	for (i = 0; i < word.size(); ++i)
		for (j = 0; j < num_tags; ++j)
			pr[i][j] = dw[i][j];
	maxprob();
}

// Compute the maximum likelihood tag based on whatever is in
// the pr field.

void MPtag::maxprob()
{
	int	i, j;
	double	m;

	for (i = 0; i < word.size(); ++i)
	{
		m = 0.0;
		for (j = 0; j < num_tags; ++j)
		{
			if (pr[i][j] > m)
			{
				m = pr[i][j];
				tag[i] = tag_to_str(j);
			}
		}
	}

	translate();
}

void MPtag::set_tagset(const string& tagset)
{
	if (option_tagset == tagset) return;

	string file_name;
	file_name = option_dir + "/medpost" + option_cnam + "." + tagset;

	filebuf fb;
	if (! fb.open(file_name.c_str(), ios::in))
	{
		cout << "Could not open " << file_name << endl;
		return;
	}

	istream is(&fb);

	string line;

	trans.clear();

	while (is.good())
	{
		getline(is, line);
		if (is.fail()) break;
		if (line.size() == 0) continue;

		int found = line.find("=>");

		if (found != string::npos)
		{
			string lhs(line.substr(0, found - 1));
			string rhs(line.substr(found + 2));

			while (lhs.size() > 0 && isspace(lhs[0])) lhs.erase(0,1);
			while (rhs.size() > 0 && isspace(rhs[0])) rhs.erase(0,1);
			while (lhs.size() > 0 && isspace(lhs[lhs.size() - 1])) lhs.erase(lhs.size() - 1,1);
			while (rhs.size() > 0 && isspace(rhs[rhs.size() - 1])) rhs.erase(rhs.size() - 1,1);

			trans[lhs] = rhs;
		}
	}

	fb.close();
	option_tagset = tagset;
}

// translate to target tag set

#define TAG_ISCONT(s) ((s).size() > 0 && (s)[(s).size()-1] == '+')

void MPtag::translate(void)
{
	if (option_tagset.size() == 0) return;

	split_idioms();

	// the way this works:

	// 1. multi word translation
	// 2. explicit word translation
	// 3. conditional (word tag) translation
	// 4. tag specific translation

	// each of the 4 steps needs to be performed becuase
	// the translation tables are written such that stages 1-3 may
	// leave medpost tags that are meant to be translated on a subsequent step

	for (int i = 0; i < word.size(); i++)
	{
		string tmp;

		// 1. if this is a multi-word
		// if fouund, translate it
		// and if no translation, remove the continuation tags

		if (TAG_ISCONT(tag[i]))
		{
			// gather the multiword together into a single string

			tmp = "";
			int w = 0;
			for (w = i; w < word.size(); w++)
			{
				if (w > i) tmp += " ";
				tmp += word[w];
				if (! TAG_ISCONT(tag[w])) break;
			}
			for (int j = 0; j < tmp.size(); j++) tmp[j] = tolower(tmp[j]);

			// see if this has an explicit translation
			// if so, parse the translation and use the new tags

			if (trans.count(tmp)>0)
			{
				string mwstr = trans[tmp];
				vector<string> mwtags;
				int pos = 0;
				while (pos < mwstr.size())
				{
					int found = mwstr.find(" ", pos);
					if (found != string::npos)
					{
						mwtags.push_back(mwstr.substr(pos, found - pos));
						pos = found + 1;
					} else
					{
						mwtags.push_back(mwstr.substr(pos));
						pos = mwstr.size();
					}
				}

				for (int j = i; j <= w; j++)
					if (mwtags[j-i] != "-") tag[j] = mwtags[j-i];
			}

			// remove any remaining continuations here

			for (int j = i; j <= w; j++) if (TAG_ISCONT(tag[j])) tag[j].erase(tag[j].size()-1,1);
		}

		// 2. see if the word has an explicit translation

		tmp = word[i];
		for (int j = 0; j < tmp.size(); j++) tmp[j] = tolower(tmp[j]);
		if (trans.count(tmp) > 0) tag[i] = trans[tmp];

		// 3. see if the word + tag has an conditional translation

		string tmp1(tmp + "_" + tag[i]);
		if (trans.count(tmp1) > 0) tag[i] = trans[tmp1];

		// 4. see if the tag has an explicit translation

		if (trans.count(tag[i]) > 0) tag[i] = trans[tag[i]];

	}
}
