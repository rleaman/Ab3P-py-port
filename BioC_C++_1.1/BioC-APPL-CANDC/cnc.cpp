/**** CNC dependency parse on the sentences in a BioC xml file
 ****/

#include <iostream>
#include <string>
#include <vector>
#include <sstream>

#include <MPtok.h>
// #include <MPtag.h>
#include <MPcandc.h>

#include "BioC.hpp"
#include "BioC_libxml.hpp"
#include "BioC_util.hpp"

using std::cerr;
using std::cout;
using std::string;
using std::vector;

using namespace BioC;

class Gram {
public:
  string type;
  vector<string> tokens;
  vector<int> positions;
};

ostream & operator<<( ostream & out, const Gram & gram ) {
  out << '(' << gram.type;
  for ( int i = 0; i < gram.tokens.size(); ++i )
    out << ' ' << gram.tokens[i] << '_' << gram.positions[i];
  out << ')';
  return out;
}

void process_tuple( const string & tuple, Gram & gram ) {
  
  if ( not ( tuple[0] == '(' and tuple[ tuple.size()-1 ] == ')' )) {
    cout << "*** bad formated tuple: " << tuple << " ***\n";
    exit(1);
  }
  
  istringstream line( tuple.substr( 1, tuple.size()-2 ) );
  line >> gram.type;
  string pair;
  while ( line >> pair ) {
    size_t underline = pair.find('_');
    if ( underline == string::npos ) {
      // no pair
      gram.tokens.push_back(pair);
      gram.positions.push_back(-1);
    }
    else if ( underline == 0 ) {
      // blank field
      gram.tokens.push_back("_");
      gram.positions.push_back(-1);
    }
    else {
      // ordinary text
      gram.tokens.push_back( pair.substr(0,underline) );
      istringstream str_position( pair.substr( underline+1 ) );
      int position;
      str_position >> position;
      gram.positions.push_back( position );
    }
  }
      
}


// allow extra spaces in source

int space_match( const string & source, string::size_type & src_pos,
                 const string & target, int & offset ) {

  // target begins with non-space

  char target_first = target[0];
  if ( target_first == ' ' )
    // target should not begin with space
    return -1;

  // skip spaces at beginning of source

  int cur_pos = src_pos;
  int src_size = source.size();
  while ( cur_pos < src_size and source[cur_pos] == ' ' )
    // find first non-space
    ++cur_pos;
  if ( cur_pos >= src_size )
    // nothing but spaces
    return -1;
  offset = cur_pos;

  // compare characters

  int i_target = 0;
  while ( i_target < target.size() ) {
      
    if ( cur_pos >= src_size )
      // ran off end of source
      return -1;
      
    if ( target[i_target] == source[cur_pos] ) {
      // match
      ++cur_pos;
      ++i_target;
      continue;
    }

    if ( source[cur_pos] == ' ' ) {
      // skip space
      ++cur_pos;
      continue;
    }

    if ( target[i_target] == '-'  and source[cur_pos] == '_' ) {
      // "fixed" match
      ++cur_pos;
      ++i_target;
      continue;
    }

    // mis-match!
    return -1;

  }

  // match

  int length = cur_pos - offset;
  src_pos = cur_pos;
  return length;
}





class CNC_Converter : public Node_Converter {
public:
  CNC_Converter() :
    r_ids("R")
  {
    tuple_relate["obj2"] = &CNC_Converter::H_D_tuple;
    tuple_relate["arg"] = &CNC_Converter::H_D_tuple;
    tuple_relate["aux"] = &CNC_Converter::H_D_tuple;
    tuple_relate["det"] = &CNC_Converter::H_D_tuple;
    tuple_relate["conj"] = &CNC_Converter::H_D_tuple;
    //    tuple_relate["mod"] = &CNC_Converter::T_H_D_tuple; // not seen
    tuple_relate["cmod"] = &CNC_Converter::T_H_D_tuple;
    tuple_relate["xmod"] = &CNC_Converter::T_H_D_tuple;
    tuple_relate["ncmod"] = &CNC_Converter::T_H_D_tuple;
    tuple_relate["iobj"] = &CNC_Converter::H_D_tuple; // only with two tokens
    //    tuple_relate["iobj"] = &CNC_Converter::T_H_D_tuple;
    tuple_relate["ccomp"] = &CNC_Converter::T_H_D_tuple;
    tuple_relate["xcomp"] = &CNC_Converter::T_H_D_tuple;
    tuple_relate["depdendent"] = &CNC_Converter::T_H_D_tuple;
    tuple_relate["arg_mod"] = &CNC_Converter::T_H_D_I_tuple;
    //    tuple_relate["subj"] = &CNC_Converter::H_D_Igr_tuple; // not seen
    //    tuple_relate["csubj"] = &CNC_Converter::H_D_Igr_tuple; // not seen
    //    tuple_relate["xsubj"] = &CNC_Converter::H_D_Igr_tuple; // not seen
    tuple_relate["ncsubj"] = &CNC_Converter::H_D_Igr_tuple;
    tuple_relate["dobj"] = &CNC_Converter::H_D_tuple; // only with two tokens
    //    tuple_relate["dobj"] = &CNC_Converter::H_D_Igf_tuple;
}

void H_D_tuple( const Gram & gram, Relation & relate ) {
  if ( gram.tokens.size() != 2 ) {
    cerr << "H_D_tuple should have 2 tokens\n";
    cerr << gram << endl;
    exit(1);
  }

  string t_id;
  t_ids.make( gram.positions[0], t_id );
  relate.nodes.push_back( Node( t_id, "head" ) );

  t_ids.make( gram.positions[1], t_id );
  relate.nodes.push_back( Node( t_id, "dependent" ) );
}

/** for now, also handles the introducer,head,dependent case
 */
void T_H_D_tuple( const Gram & gram, Relation & relate ) {
  if ( gram.tokens.size() != 3 ) {
    cerr << "T_H_D_tuple should have 3 tokens\n";
    cerr << gram << endl;
    exit(1);
  }

  string t_id;

  if ( gram.positions[0] == -1 ) {
    if ( gram.tokens[0] != "_" )
      relate.nodes.push_back( Node( gram.tokens[0], "type" ) );
  }
  else {
    t_ids.make( gram.positions[0], t_id );
    relate.nodes.push_back( Node( t_id, "type_id" ) );
  }
  
  t_ids.make( gram.positions[1], t_id );
  relate.nodes.push_back( Node( t_id, "head" ) );

  t_ids.make( gram.positions[2], t_id );
  relate.nodes.push_back( Node( t_id, "dependent" ) );
}

void T_H_D_I_tuple( const Gram & gram, Relation & relate ) {
  if ( gram.tokens.size() != 4 ) {
    cerr << "T_H_D_I_tuple should have 4 tokens\n";
    cerr << gram << endl;
    exit(1);
  }

  string t_id;

  if ( gram.positions[0] == -1 ) {
    if ( gram.tokens[0] != "_" )
      relate.nodes.push_back( Node( gram.tokens[0], "type" ) );
  }
  else {
    t_ids.make( gram.positions[0], t_id );
    relate.nodes.push_back( Node( t_id, "type_id" ) );
  }

  t_ids.make( gram.positions[1], t_id );
  relate.nodes.push_back( Node( t_id, "head" ) );

  t_ids.make( gram.positions[2], t_id );
  relate.nodes.push_back( Node( t_id, "dependent" ) );

  if ( gram.tokens[3] != "_" )
    relate.infons["initial_gr"] = gram.tokens[3];
    
}

void H_D_Igr_tuple( const Gram & gram, Relation & relate ) {
  if ( gram.tokens.size() != 3 ) {
    cerr << "T_H_D_Igr_tuple should have 3 tokens\n";
    cerr << gram << endl;
    exit(1);
  }
  
  string t_id;

  t_ids.make( gram.positions[0], t_id );
  relate.nodes.push_back( Node( t_id, "head" ) );

  t_ids.make( gram.positions[1], t_id );
  relate.nodes.push_back( Node( t_id, "dependent" ) );

  if ( gram.tokens[2] != "_" )
    relate.infons["initial_gr"] = gram.tokens[2];
  
}

void H_D_Igf_tuple( const Gram & gram, Relation & relate ) {
  if ( gram.tokens.size() != 3 ) {
    cerr << "T_H_D_Igf_tuple should have 3 tokens\n";
    cerr << gram << endl;
    exit(1);
  }
  
  string t_id;

  t_ids.make( gram.positions[0], t_id );
  relate.nodes.push_back( Node( t_id, "head" ) );

  t_ids.make( gram.positions[1], t_id );
  relate.nodes.push_back( Node( t_id, "dependent" ) );

  if ( gram.tokens[2] != "_" )
    relate.infons["initial_gf"] = gram.tokens[3];
  
}


  using Node_Converter::convert;
  
  virtual void convert( const Sentence & sentence,
                        Sentence & cnc_sentence ) {
    cnc_sentence.offset = sentence.offset;
    
    tokenize( sentence, cnc_sentence );
    vector<string> & tokens = tok.word;
    
    cnc.parse( sentence.text );
    
    for ( int i = 0; i < cnc.gr.size(); ++i ) {
      //      cout << cnc.gr[i] << '\n';
      Gram gram;
      // string & tuple = cnc.gr[i];
      process_tuple( cnc.gr[i], gram );    
      
      Relation relate;
      r_ids.next( relate.id );
      relate.infons["relation"] = gram.type;

      MP mp = tuple_relate[gram.type];
      if ( ! mp ) {
        cerr << "unexpected grammatical relation: " << gram.type << endl;
        exit(1);
      }
      (this->*mp)(gram,relate);

      // put this consistency check elsewhere

      // if ( tokens[ gram.positions[i] ] != gram.tokens[i] ) {
      //   cerr << "** inconsistent tokens: " << gram.positions[i]
      //        << ' ' << tokens[ gram.positions[i] ]
      //        << ' ' <<  gram.tokens[i] << '\n';
      //   exit(-1);
      // }
          
      cnc_sentence.relations.push_back( relate );
    }
    
  }
  

  // based on Token_Converter::convert;
  
  void tokenize( const Sentence & sentence,
                 Sentence & tokenSentence ) {
    tokenSentence.offset = sentence.offset;
    
    tok.set_segment(0);           // do not split sentences
    tok.tokenize( sentence.text );
    
    vector<string> & tokens = tok.word;
    string::size_type pos = 0;
    for ( int i = 0; i < tokens.size(); ++i ) {
      /* more reliable to use info from MPtok */
      //      string::size_type loc = sentence.text.find( tokens[i], pos );
      int offset;
      int length = space_match( sentence.text, pos, tokens[i], offset ); 
      if ( length < 0 ) { 
        cerr << "token \"" << tokens[i] << "\" not found "
          "in sentence \"" << sentence.text << "\"\n";
        exit(-1);
      }
      
      Annotation annotation;
      t_ids.make( i, annotation.id );
      annotation.infons["type"] = "token";
      annotation.add_location( sentence.offset + offset, length );
      annotation.text = sentence.text.substr(offset,length);
      tokenSentence.annotations.push_back(annotation);
      
      pos = offset + length;
    }
  }

  MPcandc cnc;
  MPtok tok;

  Seq_ID r_ids;
  Seq_ID t_ids;

  typedef void( CNC_Converter::*MP )( const Gram &, Relation & );
  map<string, MP > tuple_relate;

};


int
main(int argc, char **argv) {

  if (argc <= 1) {
    printf("Usage: %s docname\n", argv[0]);
    return(0);
  }

  char * docname = argv[1];
  Collection collection;

  Connector_libxml xml;

  xml.start_read(docname, collection);

  Collection cnc_collection;

  CNC_Converter converter;
  converter.convert( collection, cnc_collection );
  cnc_collection.key = "cnc.key";

  Connector_libxml xml_writer;
  xml_writer.start_write( "-", cnc_collection );
  
  Document document;
  while ( xml.read_next(document) ) {
    Document cnc_document;
    converter.convert( document, cnc_document );
    xml_writer.write_next( cnc_document );
  }
  
  xml_writer.end_write();

  return 0;
}
