#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <string>
#include <vector>
#include <iostream>

#include "MPcandc.h"

using namespace std;

#define BUFF_SIZE 100000

void MPcandc::iparse(string& tagged)
{
	static FILE *fp = NULL;
	static int cid = 0;
	static int fd_tochild[2];
	static int fd_toparent[2];

	gr.clear();

	if (cid == 0)
	{
		// start the child process if needed

		pipe(fd_tochild);
		pipe(fd_toparent);

		string pname = option_dir + "/candc-1.00/bin/parser";
//		cout << "Starting child process: " << pname << endl;

		cid = fork();

		if (cid == 0)		// child: /usr/bin/wc
		{
			close(0); close(1); close(2);
			dup2(fd_tochild[0],0);
			dup2(fd_toparent[1],1);
			dup2(fd_toparent[1],2);
			close(fd_toparent[0]);
			close(fd_tochild[1]);
			string pmodel = option_dir + "/candc-1.00/models/parser";
			string smodel = option_dir + "/candc-1.00/models/super_quotes";
			execl(pname.c_str(), "candc_parser", "--model", pmodel.c_str(), "--super", smodel.c_str(), NULL);
			perror("candc-1.00 process");
			exit(1);
		}

		close(fd_tochild[0]);
		close(fd_toparent[1]);
		fp = fdopen(fd_toparent[0], "r");
	}

	if (tagged.size() == 0) return;

	char *buff = (char *) malloc(BUFF_SIZE+1);
	int i;

	for (i = 0; i < tagged.size() - 1; i++) if (tagged[i] == '\n') tagged[i] = ' ';

	if (tagged[tagged.size() - 1] != '\n') tagged += '\n';

	// cout << "Parsing: " << tagged;

	write(fd_tochild[1], tagged.c_str(), tagged.size());

	while (fgets(buff, BUFF_SIZE, fp))
	{
		// cout << buff;

		if (strncmp(buff, "ERROR", 5) == 0) break;
		if (strncmp(buff, "DONE", 4) == 0) break;
		if (strncmp(buff, "<c>", 3) == 0) break;
		if (buff[0] == '(')
		{
			// remove everything after the final paren
			for (i = strlen(buff) - 1; i > 0; i--)
				if (buff[i-1] == ')')
				{
					buff[i] = '\0';
					break;
				}
			gr.push_back(buff);
		}
	}
	free(buff);
}

void MPcandc::iparse()
{
	string y;
	for (int j = 0; j < word.size(); j++)
	{
		if (j > 0) y += " ";
		y += word[j] + "|" + tag[j];
	}
	// cout << "Passing " << y << endl;

	iparse(y);
}

void MPcandc::parse(const string& sent)
{
	viterbi(sent);
	iparse();
}
