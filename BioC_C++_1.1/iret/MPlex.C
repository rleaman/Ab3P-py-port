#include <cstdio>
#include <cstring>
#include <cstdlib>

#include <iostream>
#include <string>

using namespace std;

#include "MPlex.h"

#define BUF_SIZE 1000

// #define DEBUG

int ntail = 4;

// Btree convenience macros used in programming for Hmm.C only

#define FOREACH(bt) for (bt.node_first(); bt.node_next(); )
#define REC(type, bt) ((type) bt.give_ptr())
#define STR(bt) (bt.show_str())
#define GET(b, n, w) if (! b.search(n)) { b.insert(new Node(n, (void *) w)); b.search(n); }
#define CLR(b, n) if (b.search(n)) { b.set_ptr(NULL); }
#define EXISTS(b, n) (b.search(n) && b.give_ptr())


MPlex::MPlex(int n1, int n2, const char *f, int uc)
{
        num_tags = n1;
        ntail = n2;
        addfile(f);
        use_codes = uc;
}

MPlex::~MPlex()
{
}

void MPlex::addfile(const char *f)
{
        FILE    *fp;
        char    line[BUF_SIZE];

        fp = fopen(f, "r");
        if (fp == NULL)
        {
                printf("Could not open lexicon file '%s'\n", f);
                exit(1);
        }

        while (fgets(line, BUF_SIZE, fp))
        {
                if (strchr(line, '_') == 0) continue;
                add(line);
        }

        fclose(fp);
}

void MPlex::rmfile(const char *f)
{
        FILE    *fp;
        char    line[BUF_SIZE];

        fp = fopen(f, "r");
        if (fp == NULL)
        {
                printf("Could not open lexicon file '%s'\n", f);
                exit(1);
        }

        while (fgets(line, BUF_SIZE, fp))
        {
                if (strchr(line, '_') == 0) continue;
                rm(line);
        }

        fclose(fp);
}

void MPlex::add(char *entry)
{
        char    *s, *p, *e;

        p = strchr(entry, '_');
        if (!p) return;

        string key(entry, p - entry + 1);

        for (e = p; *e && ! isspace(*e); ++e)
                ;

        tree[key] = string(p, e - p);
}

void MPlex::rm(const char *entry)
{
        char    *p;
        char    key[BUF_SIZE];

        if (strlen(entry) >= BUF_SIZE) return;

        strcpy(key, entry);

        p = strchr(key, '_');

        if (!p) return;

        p[1] = '\0';

        if (tree.count(key)) tree.erase(key);

        // CLR(tree, key);
}

#define DEFAULT_COUNT 1000.0

double MPlex::scan_lex(const char *line, char *tag)
{
        char    *s, *p;
        char    t[BUF_SIZE];
        double  v, d;

        if (! line) return 0.0;
        if (strlen(line) >= BUF_SIZE) return 0.0;

        s = strchr( const_cast<char*>(line), '_');
        while (s && *s == '_')
        {
                ++s;
                strcpy(t, s);
                s = strchr(s, '_');

                // Remove the next tag

                p = strchr(&t[1], '_');
                if (p) *p = '\0';

                // Find the count (skip the first
                // character which may itself be a ':')

                v = DEFAULT_COUNT;
                p = strchr(&t[1], ':');
                if (p)
                {
                        *p = '\0';
                        ++p;

                        v = (double) atoi(p);
                }

                // printf("%s%s%s:%g\n", word, "_", t, v);

                if (strcmp(tag, t) == 0)
                        return v;
        }
        return 0.0;
}

static double count_lex(const char *line)
{
        double  v;
        char    *p;
        char    *n;

        if (! line) return 0.0;

        v = 0.0;
        while (line && line[0] == '_')
        {
                n = strchr(const_cast<char*>(line+1), '_');
                p = strchr(const_cast<char*>(line), ':');

                // If there was a colon and it occurred before the next tag,
                // count it, otherwise use a default.

                if (p != NULL && (n == NULL || p < n))
                        v += atof(p+1);
                else
                        v += DEFAULT_COUNT;

                line = n;
        }
        return v;
}

// Return the lexicon entry, it does not need to be normalized as a probability,
// in fact it is better to return counts so that the caller can perform the
// desired smoothing.

double MPlex::get(const char *word, char *tag)
{
        const char *line = get(word);

        if (line == NULL)
        {
#ifdef DEBUG
                printf("Word %s not found in lexicon, using uniform probability.\n", word);
#endif
                return 1.0 / (double) num_tags;
        }

#if 0
        printf("Word %s found in lexicon, using %s.\n", word, line);
#endif

        // Get the word on the line

        return scan_lex(line, tag);
}

static void compact_numbers(char *buff)
{
        char    str[BUF_SIZE];
        int     i, j, in_number;

        if (strlen(buff) >= BUF_SIZE) return;

        in_number = 0;
        j = 0;
        for (i = 0; i < strlen(buff); i++)
        {
                if (isdigit(buff[i])
                || (in_number == 1 && buff[i] == '.')
                || (in_number == 0 && buff[i] == '.' && i < strlen(buff) - 1 && isdigit(buff[i+1]))
                || (in_number == 0 && (buff[i] == '-' || buff[i] == '+') && i < strlen(buff) - 1 && isdigit(buff[i+1])))
                {
                        if (! in_number)
                        {
                                in_number = 1;
                                str[j] = '1';
                                ++j;
                        }
                        if (buff[i] == '.') in_number = 2;
                } else
                {
                        in_number = 0;
                        str[j] = buff[i];
                        ++j;
                }
        }
        str[j] = '\0';
        strcpy(buff, str);
}

double MPlex::count(char *word)
{
        char    buff[BUF_SIZE + 100];
        int     i;

        if (strlen(word) >= BUF_SIZE) return 0;

        // See if the word is closed

        strcpy(buff, "^");
        strcat(buff, word);
        strcat(buff, "_");

        compact_numbers(buff);

        if (tree.count(buff))
                return count_lex(tree[buff].c_str());

        // if (EXISTS(tree, buff))
                // return count_lex(REC(char *, tree));

        // Try the lower case version

        for (i = 0; buff[i]; ++i) buff[i] = tolower(buff[i]);

        if (tree.count(buff))
                return count_lex(tree[buff].c_str());

        // if (EXISTS(tree, buff))
                // return count_lex(REC(char *, tree));

        return 0;
}

const char *MPlex::get(const char *word)
{
        char    buff[BUF_SIZE + 100], *s, *e;
        int     i;

        if (strlen(word) >= BUF_SIZE) return NULL;

        // See if the word is closed

        strcpy(buff, "^");
        strcat(buff, word);
        strcat(buff, "_");

        compact_numbers(buff);

        if (tree.count(buff))
        {
#if 0
                printf("word %s, lex entry %s is %s\n", word, buff, e);
#endif
                return tree[buff].c_str();
        }

        // Try the lower case version

        for (i = 0; buff[i]; ++i) buff[i] = tolower(buff[i]);

        if (tree.count(buff))
        {
#if 0
                printf("word %s, lex entry %s is %s\n", word, buff, e);
#endif
                return tree[buff].c_str();
        }


        // Get the search string corresponding to the word

        if (use_codes)
                search_string(buff, word);
        else
                strcpy(buff, word);
        strcat(buff, "_");

        for (s = &buff[0]; strlen(s) > 0; s++)
        {
                if (strlen(s) > ntail + 1) continue;

#if 0
                printf("looking for word '%s', search string is '%s'\n", word, s);
#endif

                if (tree.count(s))
                {
#if 0
                        printf("word '%s', lex entry %s is %s\n", word, s, e);
#endif
                        return tree[s].c_str();
                }
        }

#if 0
        printf("word %s, lex entry not found\n", word);
#endif
        return NULL;
}

int MPlex::exists(char *word)
{
        char    buff[BUF_SIZE + 100];
        int     i;

        if (strlen(word) >= BUF_SIZE) return 0;

        strcpy(buff, "^");
        strcat(buff, word);
        strcat(buff, "_");

        for (i = 0; i < strlen(buff); ++i) buff[i] = tolower(buff[i]);

        return tree.count(buff);
        // return EXISTS(tree, buff);
}

void MPlex::search_string(char *buff, const char *word)
{
        int     in_num;

        int     i, j;

        int     num_A = 0;      // Upper case
        int     num_L = 0;      // Lower case
        int     num_N = 0;      // Numbers
        int     num_P = 0;      // Punctuation (numeric)
        int     num_Q = 0;      // Quotes
        int     num_O = 0;      // Other

        char    last_ch;
        const char *p;

        if (strlen(word) == 1)
        {
                if ((word[0] >= 'a' && word[0] <= 'z')
                || (word[0] >= 'A' && word[0] <= 'Z'))
                {
                        buff[0] = tolower(word[0]);
                        buff[1] = 'S';
                        buff[2] = '\0';
                        return;
                } else if (word[0] >= '0' && word[0] <= '9')
                {
                        buff[0] = 'I';
                        buff[1] = '\0';
                        return;
                }
        }

        // Get the last word in a hyphenated list

        p = strrchr(word, '-');
        if (p == NULL || strlen(p) <= 2) p = word;
        // if (p == NULL) p = word;

#if 0
        if (p != word)
        {
                printf("word %s using %s\n", word, p);
        }
#endif

        for (i = 0; i < strlen(p); ++i)
        {
                if (i == 0 && p[i] == '-')
                        ++num_L;
                else if (p[i] >= 'a' && p[i] <= 'z')
                        ++num_L;
                else if (p[i] >= 'A' && p[i] <= 'Z')
                        ++num_A;
                else if (p[i] >= '0' && p[i] <= '9')
                        ++num_N;
                else if (strchr("=:+.,", p[i]))
                        ++num_P;
                else if (strchr("`'", p[i]))
                        ++num_Q;
                else
                        ++num_O;

                last_ch = p[i];
        }


        strcpy(buff, word);
        for (i = 0; i < strlen(buff); ++i) buff[i] = tolower(buff[i]);
        i = strlen(buff) - ntail;
        if (i < 0) i = 0;
        j = strlen(buff) - 1;
        while (j > i && buff[j] >= 'a' && buff[j] <= 'z') --j;

        strcpy(buff, word + i);
        for (i = 0; i < strlen(buff); ++i) buff[i] = tolower(buff[i]);

        if (num_L + num_Q == strlen(p)) strcat(buff, "");
        else if (num_A + num_Q == strlen(p)) strcat(buff, "A");
        else if (num_N + num_P + num_Q == strlen(p)) strcat(buff, "N");
        else if (num_L + num_A + num_Q == strlen(p)) strcat(buff, "B");
        else if (num_A + num_N + num_P + num_Q == strlen(p)) strcat(buff, "C");
        else if (num_L + num_N + num_P + num_Q == strlen(p)) strcat(buff, "E");
        else if (num_A + num_L + num_N + num_P + num_Q == strlen(p)) strcat(buff, "D");
        else if (num_O == 0 && last_ch == '+') strcat(buff, "F");
        else strcat(buff, "O");
}

#ifdef MAIN
main()
{
        MPlex l(44);
        char buff[BUF_SIZE], *s;
        double  v;

        while (gets(buff))
        {
                if (strlen(buff) == 0) exit(0);

                s = l.get(buff);
                if (s)
                {
                        printf("%s\n", s);
                } else
                        printf("not found\n");

                v = l.get(buff, "NNS");
                printf("NNS: %g\n", v);

        }
}
#endif
