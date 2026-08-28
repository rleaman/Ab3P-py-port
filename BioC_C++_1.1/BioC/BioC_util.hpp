/**** Utility class useful for working with BioC structures
 ****/

#include "BioC.hpp"
#include <sstream>

namespace BioC {

/**** Node_Converter
      Copies data elements from old object to new while descending the
      tree.

      Override methods where something interesting should happen.
****/

  class Node_Converter {
  public:

    virtual void convert( const Relation & relation,
                          Relation & new_relation );
    virtual void convert( const Annotation & annotation,
                          Annotation & new_annotation );
    virtual void convert( const Sentence & sentence,
                          Sentence & new_sentence );
    virtual void convert( const Passage & passage,
                          Passage & new_passage );
    virtual void convert( const Document & document,
                          Document & new_document );
    virtual void convert( const Collection & collection,
                          Collection & new_collection );
  };


  /**** Easily construct sequential IDs
   ****/

  class Seq_ID {
  public:
    Seq_ID( const string & in_prefix = "", int initial_num = 0 ) :
      prefix(in_prefix), next_num(initial_num)
    {}

    void make( int num, string & id ) {
      std::ostringstream ost;
      ost << prefix << num;
      id = ost.str();

      next_num = num + 1;
    }

    void next( string & id ) {
      make( next_num++, id );
    }

    // this is efficient in C++11
    string next( void ) {
      string result;
      next(result);
      return result;
    }

    string prefix;
    int next_num;
  };


}
