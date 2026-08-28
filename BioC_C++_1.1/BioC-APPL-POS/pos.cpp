/**** Identify tokens in a sentence xml file
 ****/

#include <iostream>
#include <string>
#include <vector>

#include <MPtok.h>
#include <MPtag.h>

#include "BioC.hpp"
#include "BioC_libxml.hpp"
#include "BioC_util.hpp"

using std::cout;
using std::string;
using std::vector;

using namespace BioC;

class POS_Converter : public Node_Converter {
public:
  using Node_Converter::convert;

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

  
  virtual void convert( const Sentence & sentence,
                        Sentence & posSentence ) {
    posSentence.offset = sentence.offset;
    
    tag.set_segment(0);           // do not split sentences
    tag.set_tagset("penn");
    //    tag.tokenize( sentence.text );
    tag.viterbi( sentence.text );
    /*
    cout << tag.word.size() << '\n';
    //    tag.print(0);
    for ( int i = 0; i < tag.word.size(); ++i ) {
      cout << tag.word[i] << ' ' << tag.tag[i] << '\n';
    }

    exit(0);
    */

    vector<string> & tokens = tag.word;
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
      annotation.infons["type"] = "token";
      annotation.infons["POS"] = tag.tag[i];
      annotation.add_location( sentence.offset + offset, length );
      annotation.text = sentence.text.substr(offset,length);
      posSentence.annotations.push_back(annotation);
      
      pos = offset + length;
    }

  }

  MPtag tag;

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

  xml.read(docname, collection);

  //        collection.write();

  Collection posCollection;

  POS_Converter converter;
  converter.convert( collection, posCollection );
  posCollection.key = "pos.key";

  xml.write( "-", posCollection );
        
  return 0;
}
