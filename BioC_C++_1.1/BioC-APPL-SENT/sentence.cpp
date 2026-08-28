/**** Print a collection from an XML file
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

class Sentence_Segmenter : public Node_Converter {
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


  virtual void convert( const Passage & passage,
                        Passage & passageSent ) {
    passageSent.infons = passage.infons;
    passageSent.offset = passage.offset;
  
    tok.segment( passage.text );

    vector<string> & sentences = tok.sent;
    string::size_type pos = 0;
    for ( int i = 0; i < sentences.size(); ++i ) {
      /* more reliable to use info from MPtok */

      int offset;
      int length = space_match( passage.text, pos, sentences[i], offset ); 
      if ( length < 0 ) {
        cerr << "sentence \"" << sentences[i] << "\" not found "
          "in passage \"" << passage.text << "\"\n";
        exit(-1);
      }
    
      Sentence sentence;
      sentence.offset = passage.offset + offset;
      //      sentence.text = sentences[i];
      sentence.text = passage.text.substr(offset,length);
      passageSent.sentences.push_back(sentence);
    }

  }

  MPtok tok;
};


void print_sentences( const Passage & passage ) {

  MPtok tok;
  tok.segment( passage.text );

  vector<string> & sentences = tok.sent;
  for ( int i = 0; i < sentences.size(); ++i ) {
    cout << sentences[i] << '\n';
  }

}

void print_sentences( const Document & document ) {

  for ( int i = 0; i < document.passages.size(); ++i ) {
    print_sentences( document.passages[i] );
  }
}

void print_sentences( const Collection & collection ) {

  for ( int i = 0; i < collection.documents.size(); ++i ) {
    print_sentences( collection.documents[i] );
  }
}


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

  Collection sentenceCollection;

  Sentence_Segmenter segmenter;
  segmenter.convert( collection, sentenceCollection );
  sentenceCollection.key = "sentence.key";

  Connector_libxml xml_writer;
  xml_writer.start_write("-", sentenceCollection);
 
  Document document;
  //  int count = 0;
  while ( xml.read_next(document) ) {
    Document sentenceDocument;
    segmenter.convert( document, sentenceDocument );
    xml_writer.write_next( sentenceDocument );
    //    if ( count >= 3251 )
    //      break;
    //    ++count;
  }
  
  xml_writer.end_write();
  
  return 0;
}
