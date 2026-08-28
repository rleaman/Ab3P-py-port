/**** Identify tokens in a sentence xml file
 ****/

#include <iostream>
#include <string>
#include <vector>

#include <MPtok.h>

#include "BioC.hpp"
#include "BioC_libxml.hpp"
#include "BioC_util.hpp"

using std::cout;
using std::string;
using std::vector;

using namespace BioC;

class Token_Converter : public Node_Converter {
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
      annotation.infons["type"] = "token";
      annotation.add_location( sentence.offset + offset, length );
      annotation.text = sentence.text.substr(offset,length);
      tokenSentence.annotations.push_back(annotation);
      
      pos = offset + length;
    }
  }

  MPtok tok;

};


int
main(int argc, char **argv) {

  if (argc <= 1) {
    printf("Usage: %s docname\n", argv[0]);
    return -1;
  }

  char * docname = argv[1];
  Collection collection;

  Connector_libxml xml;
  xml.start_read(docname, collection);

  Collection tokenCollection;

  Token_Converter converter;
  converter.convert( collection, tokenCollection );
  tokenCollection.key = "tokens.key";

  Connector_libxml xml_writer;
  xml_writer.start_write("-", tokenCollection);
 
  Document document;
  while ( xml.read_next(document) ) {
    Document tokenDocument;
    converter.convert( document, tokenDocument );
    xml_writer.write_next( tokenDocument );
  }
  
  xml_writer.end_write();
          
  return 0;
}
