#include "Ab3P.h"

Ab3P::Ab3P ( void ) :
  buffer(""),
  wrdData( new WordData ) 
{
    
  string sf_grp, sf_nchr, strat;
  double value; 

  char file_name[1000];
  get_pathw( file_name, "Ab3P", "prec", "dat" );
  ifstream fin(file_name);
  if(!fin) {
    cout << "Cannot open Ab3P_prec.dat\n";
    exit(1);
  }
  //get precision of a given #-ch SF's strategy
  while(fin>>sf_grp>>sf_nchr>>strat) {
    fin>>value; //precision 
    stratPrec.insert(pair<string, double>(sf_grp+sf_nchr+strat, value));
    util.push_back_strat(sf_grp+sf_nchr, strat); //set strategy sequence
  }
}

void Ab3P::get_abbrs( char * text, vector<AbbrOut> & abbrs ) {
    abbrs.clear();

    if( ! text[0] ) return; // skip empty line

    ab.Proc(text); //extract potential SF & LF pairs


    for(int i=0; i<ab.abb.size(); i++) {
      AbbrOut result;

      //      cout << "SF: " << ab.abb[i].abbs << "\n";
      //      cout << "LF: " << ab.abb[i].abbl << "\n";

      
      try_pair( ab.abb[i], result );
      
      // preserve results
      if ( result.prec > 0 ) {
        abbrs.push_back( result );
      }
    }
    ab.cleara();

  }


void Ab3P::try_pair( const Pot_Abbr & p_ab, AbbrOut & result ) {
  
  //process i) lf (sf)
  try_strats_pot_abbr( p_ab, false, result );
  
  //process ii) sf (lf)

  Pot_Abbr p_ab_swap;

  p_ab_swap.abbl = p_ab.abbs;
  p_ab_swap.abbl_tokens = p_ab.abbs_tokens;
  p_ab_swap.orig_abbl = p_ab.orig_abbs;
  
  p_ab_swap.abbs = new char[ strlen( p_ab.abbl_tokens.back() ) + 1 ];
  strcpy( p_ab_swap.abbs, p_ab.abbl_tokens.back() );
  p_ab_swap.abbs[ strlen( p_ab.abbl_tokens.back() ) ] = '\0';
  p_ab_swap.abbs_tokens.push_back( p_ab.abbl_tokens.back() );
  p_ab_swap.orig_abbs = p_ab.abbl_tokens.back();

  try_strats_pot_abbr( p_ab_swap, true, result );
}


void Ab3P::try_strats_pot_abbr ( const Pot_Abbr & abb, bool swap,
                                 AbbrOut & result ) {
      
  string sfg; //SF group eg) Al1, Num2, Spec3
  //false if sf is not ok, sfg will be assigned

  if(!util.group_sf(abb.abbs, abb.abbl, sfg )) return;
  if (swap) if(!util.exist_upperal( abb.abbs )) return;

  char sf[1000], sfl[1000];

  //strategy sequence for a given #-ch SF group
  vector<string> strats = util.get_strats(sfg);
  util.remove_nonAlnum(abb.abbs,sf); //sf will be w/o non-alnum

  //go through strategies
  for( int j=0; j<strats.size(); j++) { 
    AbbrStra * strat =
      util.strat_factory(strats[j]); //set a paticular strategy
    strat->wData = wrdData; //set wordset, stopword
    strat->abbl_tokens = &(abb.abbl_tokens);
    strat->orig_abbl = abb.orig_abbl;
    if(strat->strategy(sf, abb.abbl )) { //case sensitive
      strat->str_tolower(sf,sfl);

      if( strat->lf_ok( abb.abbs, strat->lf) ) {

        // compare AbbrStra tokens and Pot_Abbr tokens
        if ( abb.abbl_tokens.size() != strat->ntk ) {
          cerr << "different number of tokens: "
               << abb.abbl_tokens.size() << ' ' <<strat->ntk
               << '\n';
          cerr << "Pot_Abbr tokens:\n";
          for ( int it = 0; it < abb.abbl_tokens.size(); ++it ) {
            cerr << abb.abbl_tokens[it].text << '\n';
          }
          cerr << "AbbrStra tokens:\n";
          for ( int it = 0; it < strat->ntk; ++it ) {
            cerr << strat->tok[it] << '\n';
          }
          exit(-1);
        }
        for ( int it = 0; it < abb.abbl_tokens.size(); ++it ) {
          if ( abb.abbl_tokens[it].text != strat->tok[it] ) {
            cerr << "tokens differ: " << abb.abbl_tokens[it].text
                 << ' ' << strat->tok[it] << '\n';
            exit(-1);
          }
        }


        map<string, double>::iterator p =
          stratPrec.find(sfg+strats[j]);
        if(p==stratPrec.end()) {
          cerr << "No precision assigned" << endl;
          exit(1);
        }

        //add outputs 
        if( p->second>result.prec ) {
          //          result.sf = abb.abbs;
          result.sf = abb.orig_abbs;
          result.sf_offset = abb.abbs_tokens[0].offset;
          result.lf = strat->lf;
          result.lf_offset = abb.abbl_tokens[strat->lf_begin_token].offset;
          result.prec = p->second;
          result.strat = strats[j];
        }

        delete strat;
        return;
      }
    }
    delete strat;
  }

}
